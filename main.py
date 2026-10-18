import os
import io
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Query, status, UploadFile, File, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_

from .database import engine, Base, get_db, SessionLocal
from .models import Admin, Employee, Task, TaskSource, DepartmentInfo, Setting, SyncLog, ImportLog
from .auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_admin, require_auth, seed_default_users
)
from .status_classifier import (
    get_tashkent_today_iso,
    parse_and_validate_date,
    calculate_days_delayed,
    classify_task_status,
    normalize_string
)
from .excel_processor import (
    STANDARD_SOURCES,
    upload_and_replace_source_excel,
    refresh_all_task_sources,
    parse_excel_file,
    get_employee_lookup_maps,
    TASKS_DIR,
    UPLOADS_DIR,
    EMPLOYEES_UPLOAD_DIR
)

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ijro Intizomi Monitoring Dashboard API",
    version="2.0.0",
    docs_url="/docs"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Ensure required directories exist in persistent storage
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EMPLOYEES_UPLOAD_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)

# Mount static uploads
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        # Seed default admin and viewer accounts
        seed_default_users(db)

        # Seed standard task sources if empty
        for src in STANDARD_SOURCES:
            existing = db.query(TaskSource).filter(TaskSource.id == src["id"]).first()
            if not existing:
                db.add(TaskSource(
                    id=src["id"],
                    name=src["name"],
                    type="uploaded",
                    status="active",
                    total_records=0
                ))
        db.commit()
    except Exception as e:
        print(f"Startup notice: {e}")
    finally:
        db.close()

# Helper for employee auto ID generation (Requirement 9)
def generate_next_employee_id(db: Session) -> str:
    employees = db.query(Employee).all()
    max_num = 0
    for emp in employees:
        match = re.match(r"^EMP(\d+)$", str(emp.employee_id or "").strip(), re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    setting_row = db.query(Setting).filter(Setting.key == "last_employee_seq").first()
    last_seq = int(setting_row.value) if setting_row and setting_row.value and setting_row.value.isdigit() else 0
    next_seq = max(max_num, last_seq) + 1

    if setting_row:
        setting_row.value = str(next_seq)
    else:
        db.add(Setting(key="last_employee_seq", value=str(next_seq)))
    db.commit()

    return f"EMP{next_seq:04d}"

# Helper to get setting
def get_setting_val(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value else default

# =========================================================================
# 1. AUTHENTICATION (Requirement 4 & 14)
# =========================================================================

@app.post("/api/auth/login")
def login(payload: Dict[str, Any], db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    login_type = payload.get("login_type") or "viewer"

    if not username or not password:
        raise HTTPException(status_code=400, detail="Foydalanuvchi nomi va parol kiritilishi shart")

    user = db.query(Admin).filter(Admin.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Noto'g'ri foydalanuvchi nomi yoki parol")

    user_role = (user.role or "admin").lower()

    # Requirement 4: Role enforcement
    if login_type == "admin" and user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Kuzatuvchi (viewer) administrator paneliga kira olmaydi. Iltimos, /dashboard-login orqali kiring."
        )

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(data={"sub": user.username, "role": user_role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user_role
        }
    }

@app.get("/api/auth/me")
def get_me(user: Admin = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role or "viewer"
    }

@app.post("/api/auth/logout")
def logout(user: Admin = Depends(require_auth)):
    return {"message": "Muvaffaqiyatli chiqildi"}

# =========================================================================
# 2. DASHBOARD / UMUMIY KO'RINISH (Preserve Calculations & Business Logic)
# =========================================================================

def evaluate_task_dynamic(task: Task, today_iso: str) -> Dict[str, Any]:
    deadline_iso = task.deadline_iso or ""
    if not deadline_iso and task.muddat:
        parsed = parse_and_validate_date(task.muddat)
        if parsed["valid"] and parsed["iso"]:
            deadline_iso = parsed["iso"]

    return classify_task_status(
        raw_status=task.raw_status or task.holat or "",
        percentage=task.bajarilish_foizi or 0.0,
        deadline_iso=deadline_iso,
        today_iso=today_iso,
        is_overdue_flag=bool(task.is_overdue)
    )

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    task_type: Optional[str] = None,
    boshqarma: Optional[str] = None,
    source_id: Optional[str] = None,
    user: Admin = Depends(require_auth),
    db: Session = Depends(get_db)
):
    today_iso = get_tashkent_today_iso()
    query = db.query(Task)

    if task_type and task_type != "all":
        query = query.filter(or_(Task.task_type == task_type, Task.topshiriq_turi == task_type))
    if boshqarma and boshqarma != "all":
        query = query.filter(or_(Task.boshqarma == boshqarma, Task.masul == boshqarma))
    if source_id and source_id != "all":
        query = query.filter(Task.source_id == source_id)

    tasks = query.all()
    total = len(tasks)

    last_sync = get_setting_val(db, "last_successful_sync", datetime.utcnow().isoformat())
    sync_status = get_setting_val(db, "sync_status", "success")
    sync_message = get_setting_val(db, "sync_message", "Barcha ma'lumotlar dolzarb")

    if total == 0:
        return {
            "jami_topshiriqlar": 0,
            "bajarish_jarayonida": 0,
            "jarayonda": 0,
            "muddati_otgan": 0,
            "bajarilgan": 0,
            "tekshirish_zarur": 0,
            "current_date": today_iso,
            "songgi_yangilanish": last_sync,
            "sync_status": sync_status,
            "sync_message": sync_message
        }

    bajarilgan = 0
    bajarish_jarayonida = 0
    muddati_otgan = 0
    tekshirish_zarur = 0

    for t in tasks:
        ev = evaluate_task_dynamic(t, today_iso)
        if ev["is_completed"]:
            bajarilgan += 1
        elif ev["is_overdue"]:
            muddati_otgan += 1
        else:
            bajarish_jarayonida += 1
            if ev["needs_verification"]:
                tekshirish_zarur += 1

    return {
        "jami_topshiriqlar": total,
        "bajarish_jarayonida": bajarish_jarayonida,
        "jarayonda": bajarish_jarayonida,
        "muddati_otgan": muddati_otgan,
        "bajarilgan": bajarilgan,
        "tekshirish_zarur": tekshirish_zarur,
        "current_date": today_iso,
        "songgi_yangilanish": last_sync,
        "sync_status": sync_status,
        "sync_message": sync_message
    }

@app.get("/api/dashboard/departments")
def get_dashboard_departments(
    task_type: Optional[str] = None,
    user: Admin = Depends(require_auth),
    db: Session = Depends(get_db)
):
    today_iso = get_tashkent_today_iso()
    query = db.query(Task)
    if task_type and task_type != "all":
        query = query.filter(or_(Task.task_type == task_type, Task.topshiriq_turi == task_type))

    tasks = query.all()
    depts_map = {}

    for t in tasks:
        dept_name = (t.boshqarma or "Belgilanmagan").strip()
        assignee = (t.masul or "").strip()

        group_key = dept_name
        if ("BOSHQARMA BOSHLIG" in dept_name.upper() or dept_name in ("Belgilanmagan", "Belgilanmagan boshqarma") or dept_name.startswith("Mas'ul:")) and assignee and assignee != "Belgilanmagan":
            group_key = assignee

        if group_key not in depts_map:
            depts_map[group_key] = {
                "boshqarma": group_key,
                "rahbar_fish": assignee if (assignee and assignee != "Belgilanmagan") else group_key,
                "employee_id": t.employee_id or "",
                "muddati_otgan": 0,
                "max_days_delayed": 0
            }

        item = depts_map[group_key]
        if not item["employee_id"] and t.employee_id:
            item["employee_id"] = t.employee_id

        ev = evaluate_task_dynamic(t, today_iso)
        if ev["is_overdue"]:
            item["muddati_otgan"] += 1
            if ev["days_delayed"] > item["max_days_delayed"]:
                item["max_days_delayed"] = ev["days_delayed"]

    emp_by_id, emp_by_name, emp_by_dept = get_employee_lookup_maps(db)
    result = []

    for name, stats in depts_map.items():
        if stats["muddati_otgan"] <= 0:
            continue

        name_to_use = stats["rahbar_fish"] or name
        initials = "RH"
        if name_to_use:
            parts = name_to_use.split()
            if len(parts) >= 2:
                initials = f"{parts[0][0]}{parts[1][0]}".upper()
            elif len(parts) == 1:
                initials = parts[0][:2].upper()

        # Employee matching: 1. ID -> 2. Name -> 3. Dept
        matched_emp = None
        if stats["employee_id"] and stats["employee_id"].strip().upper() in emp_by_id:
            matched_emp = emp_by_id[stats["employee_id"].strip().upper()]
        else:
            norm_name = normalize_string(name_to_use)
            if norm_name in emp_by_name:
                matched_emp = emp_by_name[norm_name]
            else:
                parts = norm_name.split()
                if len(parts) >= 2 and f"{parts[0]} {parts[1]}" in emp_by_name:
                    matched_emp = emp_by_name[f"{parts[0]} {parts[1]}"]
                elif stats["boshqarma"]:
                    norm_dept = normalize_string(stats["boshqarma"])
                    if norm_dept in emp_by_dept:
                        matched_emp = emp_by_dept[norm_dept]

        photo_url = matched_emp.photo_url if (matched_emp and matched_emp.photo_url) else ""
        final_name = matched_emp.full_name if (matched_emp and matched_emp.full_name) else name_to_use

        result.append({
            "boshqarma": stats["boshqarma"],
            "rahbar_fish": final_name,
            "rahbar_rasmi": photo_url,
            "rahbar_harflari": initials,
            "rahbar_lavozimi": matched_emp.position if matched_emp else "",
            "employee_id": matched_emp.employee_id if matched_emp else stats["employee_id"],
            "muddati_otgan": stats["muddati_otgan"],
            "max_days_delayed": stats["max_days_delayed"],
            "rank": 1
        })

    # Sort descending by overdue count
    result.sort(key=lambda x: x["muddati_otgan"], reverse=True)
    for idx, r in enumerate(result, start=1):
        r["rank"] = idx

    return result

@app.get("/api/dashboard/types")
@app.get("/api/task-types")
def get_task_types(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    today_iso = get_tashkent_today_iso()
    tasks = db.query(Task).all()
    type_map = {}

    for t in tasks:
        t_name = (t.topshiriq_turi or t.task_type or "Prezident topshiriqlari").strip()
        if t_name not in type_map:
            type_map[t_name] = {
                "type": t_name,
                "name": t_name,
                "source_id": t_name,
                "jami": 0,
                "bajarish_jarayonida": 0,
                "muddati_otgan": 0,
                "bajarilgan": 0,
                "summary": {
                    "jami": 0,
                    "bajarish_jarayonida": 0,
                    "muddati_otgan": 0,
                    "bajarilgan": 0
                }
            }

        item = type_map[t_name]
        item["jami"] += 1
        item["summary"]["jami"] += 1

        ev = evaluate_task_dynamic(t, today_iso)
        if ev["is_completed"]:
            item["bajarilgan"] += 1
            item["summary"]["bajarilgan"] += 1
        elif ev["is_overdue"]:
            item["muddati_otgan"] += 1
            item["summary"]["muddati_otgan"] += 1
        else:
            item["bajarish_jarayonida"] += 1
            item["summary"]["bajarish_jarayonida"] += 1

    res = list(type_map.values())
    res.sort(key=lambda x: x["jami"], reverse=True)
    return res

@app.get("/api/dashboard/document-types")
@app.get("/api/document-types")
def get_document_types(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    today_iso = get_tashkent_today_iso()
    tasks = db.query(Task).all()
    doc_map = {}

    for t in tasks:
        d_name = (t.hujjat_turi or "Qaror").strip()
        if d_name not in doc_map:
            doc_map[d_name] = {
                "type": d_name,
                "name": d_name,
                "source_id": d_name,
                "jami": 0,
                "bajarish_jarayonida": 0,
                "muddati_otgan": 0,
                "bajarilgan": 0,
                "summary": {
                    "jami": 0,
                    "bajarish_jarayonida": 0,
                    "muddati_otgan": 0,
                    "bajarilgan": 0
                }
            }

        item = doc_map[d_name]
        item["jami"] += 1
        item["summary"]["jami"] += 1

        ev = evaluate_task_dynamic(t, today_iso)
        if ev["is_completed"]:
            item["bajarilgan"] += 1
            item["summary"]["bajarilgan"] += 1
        elif ev["is_overdue"]:
            item["muddati_otgan"] += 1
            item["summary"]["muddati_otgan"] += 1
        else:
            item["bajarish_jarayonida"] += 1
            item["summary"]["bajarish_jarayonida"] += 1

    res = list(doc_map.values())
    res.sort(key=lambda x: x["jami"], reverse=True)
    return res

@app.get("/api/dashboard/charts")
def get_dashboard_charts(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    today_iso = get_tashkent_today_iso()
    tasks = db.query(Task).all()

    in_progress = 0
    overdue = 0
    completed = 0
    type_counts = {}

    for t in tasks:
        ev = evaluate_task_dynamic(t, today_iso)
        if ev["is_completed"]:
            completed += 1
        elif ev["is_overdue"]:
            overdue += 1
        else:
            in_progress += 1

        t_type = (t.topshiriq_turi or t.task_type or "Prezident topshiriqlari").strip()
        type_counts[t_type] = type_counts.get(t_type, 0) + 1

    dept_perf = [{"name": k, "value": v} for k, v in type_counts.items()]
    dept_perf.sort(key=lambda x: x["value"], reverse=True)

    return {
        "status_distribution": [
            {"name": "Bajarish jarayonida", "value": in_progress},
            {"name": "Muddati o'tgan", "value": overdue},
            {"name": "Bajarilgan", "value": completed}
        ],
        "department_performance": dept_perf,
        "monthly_trend": []
    }

# =========================================================================
# 3. TASKS ENDPOINTS
# =========================================================================

@app.get("/api/tasks")
def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: Optional[str] = None,
    boshqarma: Optional[str] = None,
    holat: Optional[str] = None,
    task_type: Optional[str] = None,
    topshiriq_turi: Optional[str] = None,
    hujjat_turi: Optional[str] = None,
    source_id: Optional[str] = None,
    user: Admin = Depends(require_auth),
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    today_iso = get_tashkent_today_iso()

    if search:
        s_pat = f"%{search.strip()}%"
        query = query.filter(or_(
            Task.topshiriq.ilike(s_pat),
            Task.masul.ilike(s_pat),
            Task.boshqarma.ilike(s_pat),
            Task.employee_id.ilike(s_pat)
        ))

    if boshqarma and boshqarma != "all":
        query = query.filter(or_(Task.boshqarma == boshqarma, Task.masul == boshqarma))

    if task_type and task_type != "all":
        query = query.filter(or_(Task.task_type == task_type, Task.topshiriq_turi == task_type))
    if topshiriq_turi and topshiriq_turi != "all":
        query = query.filter(or_(Task.task_type == topshiriq_turi, Task.topshiriq_turi == topshiriq_turi))
    if hujjat_turi and hujjat_turi != "all":
        query = query.filter(Task.hujjat_turi == hujjat_turi)
    if source_id and source_id != "all":
        query = query.filter(Task.source_id == source_id)

    # Dynamic status filter
    if holat and holat != "all":
        all_matched = query.all()
        filtered = []
        for t in all_matched:
            ev = evaluate_task_dynamic(t, today_iso)
            if holat in ("Muddati o‘tgan", "Muddati o'tgan", "overdue") and ev["is_overdue"]:
                filtered.append(t)
            elif holat in ("Bajarildi", "Bajarilgan", "completed") and ev["is_completed"]:
                filtered.append(t)
            elif holat in ("Jarayonda", "Bajarish jarayonida", "in_progress") and not ev["is_completed"] and not ev["is_overdue"]:
                filtered.append(t)
        total = len(filtered)
        start = (page - 1) * page_size
        items = filtered[start:start + page_size]
    else:
        total = query.count()
        items = query.order_by(desc(Task.is_overdue), asc(Task.days_remaining)).offset((page - 1) * page_size).limit(page_size).all()

    emp_by_id, emp_by_name, _ = get_employee_lookup_maps(db)
    result_items = []
    for t in items:
        ev = evaluate_task_dynamic(t, today_iso)
        # Lookup photo
        photo = ""
        matched_name = t.masul
        if t.employee_id and t.employee_id.strip().upper() in emp_by_id:
            photo = emp_by_id[t.employee_id.strip().upper()].photo_url or ""
            matched_name = emp_by_id[t.employee_id.strip().upper()].full_name
        elif t.masul:
            nname = normalize_string(t.masul)
            if nname in emp_by_name:
                photo = emp_by_name[nname].photo_url or ""
                matched_name = emp_by_name[nname].full_name

        result_items.append({
            "id": t.id,
            "task_type": t.task_type or t.topshiriq_turi,
            "topshiriq_turi": t.topshiriq_turi or t.task_type,
            "hujjat_turi": t.hujjat_turi,
            "topshiriq": t.topshiriq,
            "boshqarma": t.boshqarma,
            "masul": matched_name or t.masul,
            "employee_id": t.employee_id,
            "employee_photo": photo,
            "berilgan_sana": t.berilgan_sana,
            "muddat": t.muddat,
            "deadline_iso": deadline_iso,
            "holat": ev["status"],
            "bajarilish_foizi": t.bajarilish_foizi,
            "ustuvorlik": t.ustuvorlik,
            "izoh": t.izoh,
            "days_remaining": t.days_remaining,
            "days_delayed": ev.get("days_delayed", 0),
            "is_overdue": ev.get("is_overdue", False),
            "source_id": t.source_id,
            "source_file": t.source_file
        })

    return {
        "total": total,
        "items": result_items,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size)
    }

@app.get("/api/tasks/sources")
def get_task_sources(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    sources = db.query(TaskSource).order_by(TaskSource.id.asc()).all()
    res = []
    for s in sources:
        cnt = db.query(Task).filter(Task.source_id == s.id).count()
        res.append({
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "original_filename": s.original_filename,
            "updated_at": s.updated_at,
            "status": s.status,
            "total_records": cnt,
            "current_task_count": cnt
        })
    return res

# Requirement 7: Atomic source upload & replacement
@app.post("/api/tasks/sources/{source_id}/upload")
async def upload_task_source(
    source_id: str,
    file: UploadFile = File(...),
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Faqat Excel (.xlsx, .xls) fayllari qabul qilinadi")

    content = await file.read()
    res = upload_and_replace_source_excel(db, source_id, file.filename, content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Faylni yuklashda xatolik yuz berdi"))
    return res

@app.post("/api/tasks/sources/{source_id}/refresh")
def refresh_task_source(
    source_id: str,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    source_dir = os.path.join(TASKS_DIR, source_id)
    current_excel = os.path.join(source_dir, "current.xlsx")
    if not os.path.exists(current_excel):
        raise HTTPException(status_code=404, detail="Ushbu manbada mavjud Excel fayli topilmadi")

    with open(current_excel, "rb") as f:
        file_bytes = f.read()

    src = db.query(TaskSource).filter(TaskSource.id == source_id).first()
    orig_name = src.original_filename if src and src.original_filename else "current.xlsx"
    res = upload_and_replace_source_excel(db, source_id, orig_name, file_bytes)
    return res

@app.delete("/api/tasks/sources/{source_id}")
def delete_task_source(
    source_id: str,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    db.query(Task).filter(Task.source_id == source_id).delete()
    src = db.query(TaskSource).filter(TaskSource.id == source_id).first()
    if src:
        src.total_records = 0
        src.status = "empty"
        src.original_filename = None
    db.commit()
    return {"success": True, "message": f"{source_id} muvaffaqiyatli tozalandi"}

# =========================================================================
# 4. REFRESH & SYNC STATUS (Requirement 8 & 15)
# =========================================================================

@app.get("/api/data/status")
def get_data_status(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    return {
        "status": get_setting_val(db, "sync_status", "success"),
        "message": get_setting_val(db, "sync_message", "Barcha ma'lumotlar dolzarb"),
        "last_updated": get_setting_val(db, "last_successful_sync", datetime.utcnow().isoformat()),
        "is_syncing": False,
        "total_records": db.query(Task).count()
    }

@app.post("/api/data/refresh")
@app.post("/api/data/refresh-all")
def refresh_all_data(admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    res = refresh_all_task_sources(db)
    return res

# =========================================================================
# 5. EMPLOYEE MANAGEMENT (Requirement 9 & 10 - ADMIN ONLY)
# =========================================================================

@app.get("/api/admin/employees")
def list_employees(
    search: Optional[str] = None,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Employee)
    if search:
        s_pat = f"%{search.strip()}%"
        query = query.filter(or_(
            Employee.full_name.ilike(s_pat),
            Employee.employee_id.ilike(s_pat),
            Employee.department.ilike(s_pat)
        ))
    employees = query.order_by(Employee.employee_id.asc()).all()
    return [
        {
            "id": e.id,
            "employee_id": e.employee_id,
            "full_name": e.full_name,
            "department": e.department,
            "position": e.position,
            "photo_url": e.photo_url,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None
        }
        for e in employees
    ]

@app.post("/api/admin/employees")
async def create_employee(
    full_name: str = Form(...),
    department: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    next_emp_id = generate_next_employee_id(db)
    photo_url = None

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
        ts = int(datetime.utcnow().timestamp() * 1000)
        filename = f"{next_emp_id}_{ts}{ext}"
        filepath = os.path.join(EMPLOYEES_UPLOAD_DIR, filename)
        content = await photo.read()
        with open(filepath, "wb") as f:
            f.write(content)
        photo_url = f"/uploads/employees/{filename}"

    emp = Employee(
        employee_id=next_emp_id,
        full_name=full_name.strip(),
        department=(department or "").strip() or None,
        position=(position or "").strip() or None,
        photo_url=photo_url,
        created_at=datetime.utcnow()
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    return {
        "success": True,
        "message": f"Xodim muvaffaqiyatli qo'shildi ({next_emp_id})",
        "employee_id": next_emp_id,
        "employee": {
            "id": emp.id,
            "employee_id": emp.employee_id,
            "full_name": emp.full_name,
            "department": emp.department,
            "position": emp.position,
            "photo_url": emp.photo_url
        }
    }

@app.put("/api/admin/employees/{id}")
async def update_employee(
    id: int,
    full_name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    if full_name:
        emp.full_name = full_name.strip()
    if department is not None:
        emp.department = department.strip()
    if position is not None:
        emp.position = position.strip()

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
        ts = int(datetime.utcnow().timestamp() * 1000)
        filename = f"{emp.employee_id}_{ts}{ext}"
        filepath = os.path.join(EMPLOYEES_UPLOAD_DIR, filename)
        content = await photo.read()
        with open(filepath, "wb") as f:
            f.write(content)
        emp.photo_url = f"/uploads/employees/{filename}"

    emp.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": "Xodim ma'lumotlari muvaffaqiyatli yangilandi",
        "employee": {
            "id": emp.id,
            "employee_id": emp.employee_id,
            "full_name": emp.full_name,
            "department": emp.department,
            "position": emp.position,
            "photo_url": emp.photo_url
        }
    }

@app.delete("/api/admin/employees/{id}")
def delete_employee(
    id: int,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    db.delete(emp)
    db.commit()
    return {"success": True, "message": "Xodim o'chirildi"}

@app.post("/api/admin/employees/{id}/photo")
async def upload_employee_photo(
    id: int,
    photo: UploadFile = File(...),
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
    ts = int(datetime.utcnow().timestamp() * 1000)
    filename = f"{emp.employee_id}_{ts}{ext}"
    filepath = os.path.join(EMPLOYEES_UPLOAD_DIR, filename)
    content = await photo.read()
    with open(filepath, "wb") as f:
        f.write(content)

    emp.photo_url = f"/uploads/employees/{filename}"
    emp.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "photo_url": emp.photo_url,
        "message": "Fotosurat muvaffaqiyatli yuklandi"
    }

@app.delete("/api/admin/employees/{id}/photo")
def delete_employee_photo(
    id: int,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    emp.photo_url = None
    emp.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Fotosurat o'chirildi"}

# =========================================================================
# 6. SETTINGS & PASSWORD
# =========================================================================

@app.post("/api/settings/change-password")
def change_password(
    payload: Dict[str, str],
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    old_pw = payload.get("old_password") or ""
    new_pw = payload.get("new_password") or ""

    if not verify_password(old_pw, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Eski parol noto'g'ri kiritildi")
    if len(new_pw) < 4:
        raise HTTPException(status_code=400, detail="Yangi parol kamida 4 ta belgidan iborat bo'lishi kerak")

    admin.hashed_password = get_password_hash(new_pw)
    db.commit()
    return {"message": "Parol muvaffaqiyatli o'zgartirildi"}

# =========================================================================
# 7. EXCEL EXPORT & TEMPLATE
# =========================================================================

@app.get("/api/export/excel")
def export_excel(
    boshqarma: Optional[str] = None,
    holat: Optional[str] = None,
    task_type: Optional[str] = None,
    user: Admin = Depends(require_auth),
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    if boshqarma and boshqarma != "all":
        query = query.filter(or_(Task.boshqarma == boshqarma, Task.masul == boshqarma))
    if task_type and task_type != "all":
        query = query.filter(or_(Task.task_type == task_type, Task.topshiriq_turi == task_type))

    tasks = query.all()
    today_iso = get_tashkent_today_iso()

    rows = []
    for t in tasks:
        ev = evaluate_task_dynamic(t, today_iso)
        rows.append({
            "ID": t.id,
            "Topshiriq turi": t.topshiriq_turi or t.task_type,
            "Hujjat turi": t.hujjat_turi,
            "Topshiriq mazmuni": t.topshiriq,
            "Boshqarma": t.boshqarma,
            "Mas'ul xodim": t.masul,
            "Berilgan sana": t.berilgan_sana or "",
            "Ijro muddati": t.muddat,
            "Holat": ev["status"],
            "Bajarilish foizi": t.bajarilish_foizi,
            "Kechikkan kunlar": ev["daysDelayed"],
            "Izoh": t.izoh or ""
        })

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Topshiriqlar")
    buf.seek(0)

    filename = f"ijro_intizomi_{today_iso}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/template/excel")
def download_template():
    columns = [
        "№", "Hujjat turi", "Topshiriq turi", "Topshiriq mazmuni",
        "Mas'ul boshqarma", "Mas'ul ijrochi", "Xodim ID",
        "Berilgan sana", "Ijro muddati", "Holat", "Bajarilish foizi", "Izoh"
    ]
    sample = [
        [1, "Qaror", "Prezident topshiriqlari", "Elektr stansiyalari modernizatsiyasi rejasini ishlab chiqish",
         "Generatsiya bosh boshqarmasi", "SALIMYOROV G'OLIB SUR'ATOVICH", "EMP0018",
         "01.01.2026", "01.12.2026", "Jarayonda", 50, "Reja tasdiqlash bosqichida"]
    ]
    df = pd.DataFrame(sample, columns=columns)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Shablon")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=shablon_ijro_intizomi.xlsx"}
    )

# Static helper endpoints for frontend select filters
@app.get("/api/sources")
def get_sources_list(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    sources = db.query(TaskSource).all()
    return [s.name for s in sources]

@app.get("/api/department-names")
def get_department_names(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    depts = db.query(Task.boshqarma).distinct().all()
    return sorted([d[0] for d in depts if d[0]])

@app.get("/api/risks")
def get_risks_data(user: Admin = Depends(require_auth), db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    today_iso = get_tashkent_today_iso()
    critical = []
    high = []
    medium = []
    low = []

    for t in tasks:
        ev = evaluate_task_dynamic(t, today_iso)
        item = {
            "id": t.id,
            "topshiriq": t.topshiriq,
            "boshqarma": t.boshqarma,
            "masul": t.masul,
            "muddat": t.muddat,
            "holat": ev["status"],
            "days_remaining": t.days_remaining
        }
        if ev["is_overdue"]:
            critical.append(item)
        elif 0 <= t.days_remaining <= 3 and not ev["is_completed"]:
            high.append(item)
        elif 4 <= t.days_remaining <= 7 and not ev["is_completed"]:
            medium.append(item)
        else:
            low.append(item)

    return {
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low
    }

# =========================================================================
# 8. SERVE REACT SPA (Single Page Application HTML5 Routing)
# =========================================================================

if os.path.exists(FRONTEND_DIST):
    # Mount Vite static assets
    vite_assets = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(vite_assets):
        app.mount("/assets", StaticFiles(directory=vite_assets), name="vite-assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        # Don't hijack API or static files
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path.startswith("docs"):
            raise HTTPException(status_code=404, detail="Not Found")

        file_target = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.exists(file_target) and os.path.isfile(file_target):
            return FileResponse(file_target)

        # HTML5 Fallback
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
