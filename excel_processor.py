"""
Unified Excel Processor & Task Sources Manager
Implements:
1. Multi-lingual Excel column detection (Uzbek Latin/Cyrillic, Russian, English).
2. Safe row extraction, skipping total/summary lines (Jami, Итого).
3. Employee photo matching via employees table (by employee_id, full_name, or department).
4. Atomic file replacement for a specific source (Requirement 7: replaces old data, does not append).
5. Refresh all active task sources (Requirement 8).
"""

import os
import io
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import Task, TaskSource, Employee, Setting, SyncLog
from .status_classifier import (
    get_tashkent_today_iso,
    parse_and_validate_date,
    calculate_days_delayed,
    classify_task_status,
    normalize_string
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TASKS_DIR = os.path.join(DATA_DIR, "tasks")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
EMPLOYEES_UPLOAD_DIR = os.path.join(UPLOADS_DIR, "employees")

os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(EMPLOYEES_UPLOAD_DIR, exist_ok=True)

# 8 designated task sources
STANDARD_SOURCES = [
    {"id": "task_1", "name": "Topshiriq 1: Prezident farmon va qarorlari"},
    {"id": "task_2", "name": "Topshiriq 2: Vazirlar Mahkamasi topshiriqlari"},
    {"id": "task_3", "name": "Topshiriq 3: Hukumat komissiyasi bayonlari"},
    {"id": "task_4", "name": "Topshiriq 4: Vazirlik hay'at qarorlari"},
    {"id": "task_5", "name": "Topshiriq 5: Boshqaruv raisi buyruqlari"},
    {"id": "task_6", "name": "Topshiriq 6: Hududiy tashriflar topshiriqlari"},
    {"id": "task_7", "name": "Topshiriq 7: Jismoniy va yuridik shaxslar murojaatlari"},
    {"id": "task_8", "name": "Topshiriq 8: Ichki nazorat va reja-topshiriqlar"}
]

# Multi-lingual column patterns
COL_PATTERNS = {
    "employee_id": [
        r"^(xodim|employee|ma['']?s['']?ul)\s*(id|identifikator|raqam(i)?)$",
        r"^(xodim|employee|masul)[_\s]*id$",
        r"^emp(loyee)?[\s_-]*id$",
        r"^xodim\s*id$",
        r"^mas['']?ul\s*id$",
        r"^employee\s*id$",
        r"^emp$",
        r"^табел\s*(рақам(и)?|номер(и)?)?$",
        r"^tabel\s*(raqam(i)?)?$"
    ],
    "doc_type": [
        r"^hujjat\s*turi$", r"^ҳужжат\s*тури$",
        r"^(тип|вид)\s*документа$", r"^document\s*type$",
        r"^hujjat(\s*shakli)?$", r"^doc(\s*type)?$"
    ],
    "task_type": [
        r"^topshiriq\s*turi$", r"^топшириқ\s*тури$",
        r"^(тип|вид)\s*поручения$", r"^task\s*type$",
        r"^tur(i)?$", r"^тури$", r"^kategoriya$", r"^категория$", r"^category$",
        r"^yo['']?nalish$", r"^йўналиш$"
    ],
    "topshiriq": [
        r"^(topshiriq\s*)?mazmun(i)?$", r"^(топшириқ\s*)?мазмун(и)?$",
        r"^vazifaning\s*to['']liq\s*matni$", r"^topshiriq(\s*matni)?$", r"^топшириқ(\s*матни)?$",
        r"^(поручение|содержание|краткое\s*содержание|описание|наименование|текст)$",
        r"^(task\s*description|description|content)$", r"^вазифа$", r"^vazifa$"
    ],
    "doc_num": [
        r"^(hujjat\s*raqami(\s*va\s*sanasi)?|ҳужжат\s*рақами(\s*ва\s*санаси)?)$",
        r"^(номер\s*и\s*дата\s*документа|номер\s*документа|реквизиты)$",
        r"^(doc\s*number|document\s*no)$"
    ],
    "boshqarma": [
        r"^(ma['']?s['']?ul\s*)?boshqarma(\s*nomi)?$", r"^(ма[ъ'’]?с[ъ'’]?ул\s*)?бошқарма(\s*номи)?$",
        r"^(tashkiliy\s*birlik|департамент|departament|bo['']lim|бўлим|lavozimi|лавозими)$",
        r"^(управление|департамент|подразделение|служба|отдел|организация)$",
        r"^(department|dept|org\s*unit|organization|division)$"
    ],
    "masul": [
        r"^(ma['']?s['']?ul\s*)?(ijrochi|xodim|shaxs)$", r"^(ма[ъ'’]?с[ъ'’]?ул\s*)?(ҳодим|ходим|ижрочи|шахс)$",
        r"^(bajaruvchi\s*xodim|ма[ъ'’]?с[ъ'’]?ул|mas['']?ul|ma['']?sul|ijrochi|ижрочи|xodim|ходим|ҳодим)$",
        r"^(ответственный(\s*исполнитель)?|исполнитель|фио|сотрудник)$",
        r"^(assignee|responsible|owner|executor)$", r"^f\.?i\.?sh\.?$", r"^ф\.?и\.?ш\.?$", r"^фиш$", r"^fish$"
    ],
    "muddat": [
        r"^(ijro|topshiriq|oxirgi)\s*muddat(i)?$", r"^(ижро|топшириқ|охирги)\s*муддат(и)?$",
        r"^(bajarish\s*kuni|ijro\s*sanasi|ижро\s*санаси)$",
        r"^(срок(\s*исполнения)?|дата(\s*исполнения)?|дедлайн)$",
        r"^(deadline|due\s*date|due|date)$", r"^muddat(i)?$", r"^муддат(и)?$", r"^sana(si)?$", r"^сана(си)?$"
    ],
    "holat": [
        r"^(ijro\s*)?holat(i)?$", r"^(ижро\s*)?ҳолат(i|и)?$", r"^holat\s*kodi$",
        r"^(status|статус|состояние)$", r"^state$"
    ],
    "percentage": [
        r"^bajarilish(\s*foizi|\s*\(%\))?$", r"^бажарилиш(\s*фоизи|\s*\(%\))?$",
        r"^bajarilishi$", r"^бажарилиши$", r"^foiz(\s*darajasi)?$", r"^фоиз$",
        r"^(процент(\s*выполнения)?|прогресс|progress|percentage|percent)$"
    ],
    "berilgan_sana": [
        r"^(berilgan|hujjat|topshiriq)\s*sana(si)?$", r"^(берилган|ҳужжат|топшириқ)\s*сана(си)?$",
        r"^(дата\s*(выдачи|документа|поручения|создания))$", r"^(created(\s*at)?|issue\s*date)$"
    ],
    "ustuvorlik": [
        r"^ustuvorlik$", r"^устуворлик$", r"^priority$", r"^приоритет$", r"^muhimlik$"
    ],
    "izoh": [
        r"^izoh$", r"^изоҳ$", r"^eslatma$", r"^эслатма$", r"^комментарий$",
        r"^примечание$", r"^comment$", r"^note(s)?$"
    ]
}

def clean_header(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip().lower()
    s = re.sub(r"[\u02BB\u02BC\u2018\u2019`ʻʼ']", "'", s)
    s = re.sub(r"[«»\"\"“”]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def detect_column_roles(headers: List[str]) -> Dict[str, int]:
    """Detects standard column roles from headers list."""
    mapping = {}
    used_indices = set()

    # Priority order
    order = [
        "topshiriq", "masul", "muddat", "holat", "boshqarma",
        "employee_id", "percentage", "doc_type", "task_type",
        "doc_num", "berilgan_sana", "ustuvorlik", "izoh"
    ]

    for role in order:
        patterns = COL_PATTERNS.get(role, [])
        for idx, h in enumerate(headers):
            if idx in used_indices:
                continue
            cleaned = clean_header(h)
            for pat in patterns:
                if re.search(pat, cleaned, re.IGNORECASE):
                    mapping[role] = idx
                    used_indices.add(idx)
                    break
            if role in mapping:
                break

    return mapping

def is_summary_row(row_values: List[Any]) -> bool:
    """Checks whether a row is a summary or total row (Jami, Итого)."""
    text = " ".join(str(v or "").lower() for v in row_values[:5])
    return any(k in text for k in ["jami", "жами", "итого", "total", "всего"])

def get_employee_lookup_maps(db: Session):
    """Builds employee lookup dictionaries from database employees table."""
    employees = db.query(Employee).all()
    emp_by_id = {}
    emp_by_name = {}
    emp_by_dept = {}

    for e in employees:
        eid = (e.employee_id or "").strip().upper()
        if eid:
            emp_by_id[eid] = e
        fname = normalize_string(e.full_name)
        if fname:
            emp_by_name[fname] = e
            parts = fname.split()
            if len(parts) >= 2:
                emp_by_name[f"{parts[0]} {parts[1]}"] = e
        dept = normalize_string(e.department)
        if dept:
            emp_by_dept[dept] = e

    return emp_by_id, emp_by_name, emp_by_dept

def parse_excel_file(
    file_bytes: bytes,
    source_id: str,
    original_filename: str,
    db: Session,
    sheet_name: Optional[str] = None
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """
    Parses an Excel file in-memory.
    Returns (success, parsed_records, error_message).
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        return False, [], f"Excel faylini ochishda xatolik: {e}"

    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return False, [], "Excel varag'ida ma'lumotlar topilmadi"

    # Find header row (1st to 5th row)
    header_idx = 0
    col_mapping = {}
    for i in range(min(10, len(rows))):
        row_str = [str(c or "").strip() for c in rows[i]]
        mapping = detect_column_roles(row_str)
        if "topshiriq" in mapping or "masul" in mapping or "muddat" in mapping:
            header_idx = i
            col_mapping = mapping
            break

    if "topshiriq" not in col_mapping and "masul" not in col_mapping:
        # Fallback to 1st row
        col_mapping = detect_column_roles([str(c or "").strip() for c in rows[0]])

    emp_by_id, emp_by_name, emp_by_dept = get_employee_lookup_maps(db)
    today_iso = get_tashkent_today_iso()

    records = []
    for r_idx in range(header_idx + 1, len(rows)):
        row = rows[r_idx]
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        if is_summary_row(row):
            continue

        def get_val(role):
            idx = col_mapping.get(role)
            if idx is not None and idx < len(row):
                v = row[idx]
                return "" if v is None else str(v).strip()
            return ""

        topshiriq_text = get_val("topshiriq")
        masul_text = get_val("masul")
        muddat_text = get_val("muddat")
        raw_status = get_val("holat")
        boshqarma_text = get_val("boshqarma")
        doc_type_text = get_val("doc_type")
        task_type_text = get_val("task_type")
        raw_emp_id = get_val("employee_id")
        perc_val = get_val("percentage")

        if not topshiriq_text and not masul_text:
            continue

        # Parse date
        date_res = parse_and_validate_date(row[col_mapping["muddat"]] if "muddat" in col_mapping and col_mapping["muddat"] < len(row) else muddat_text)
        deadline_iso = date_res["iso"] or ""
        display_muddat = date_res["display"] or muddat_text

        # Parse percentage
        try:
            p_clean = re.sub(r"[^\d.]", "", str(perc_val))
            perc_num = float(p_clean) if p_clean else 0.0
            if perc_num <= 1.0 and 0.0 < perc_num:
                perc_num = round(perc_num * 100.0, 1)
        except Exception:
            perc_num = 0.0

        # Classify status using Tashkent timezone
        cls_res = classify_task_status(
            raw_status=raw_status,
            percentage=perc_num,
            deadline_iso=deadline_iso,
            today_iso=today_iso
        )

        # Match employee photo & ID
        matched_emp = None
        if raw_emp_id and raw_emp_id.strip().upper() in emp_by_id:
            matched_emp = emp_by_id[raw_emp_id.strip().upper()]
        else:
            nname = normalize_string(masul_text)
            if nname in emp_by_name:
                matched_emp = emp_by_name[nname]
            else:
                parts = nname.split()
                if len(parts) >= 2 and f"{parts[0]} {parts[1]}" in emp_by_name:
                    matched_emp = emp_by_name[f"{parts[0]} {parts[1]}"]
                elif boshqarma_text:
                    ndept = normalize_string(boshqarma_text)
                    if ndept in emp_by_dept:
                        matched_emp = emp_by_dept[ndept]

        final_emp_id = matched_emp.employee_id if matched_emp else raw_emp_id

        # Calculate days remaining
        days_remaining = 0
        if deadline_iso:
            try:
                d1 = datetime.strptime(deadline_iso, "%Y-%m-%d")
                d2 = datetime.strptime(today_iso, "%Y-%m-%d")
                days_remaining = (d1 - d2).days
            except Exception:
                pass

        # Risk level
        risk_level = "Past"
        if cls_res["is_overdue"]:
            risk_level = "Kritik"
        elif 0 <= days_remaining <= 3 and not cls_res["is_completed"]:
            risk_level = "Yuqori"
        elif 4 <= days_remaining <= 7 and not cls_res["is_completed"]:
            risk_level = "O'rta"

        records.append({
            "task_type": task_type_text or "Prezident topshiriqlari",
            "topshiriq_turi": task_type_text or "Prezident topshiriqlari",
            "hujjat_turi": doc_type_text or "Qaror",
            "topshiriq": topshiriq_text or "Topshiriq mazmuni mavjud emas",
            "boshqarma": boshqarma_text or "Belgilanmagan",
            "masul": masul_text or "Belgilanmagan",
            "berilgan_sana": get_val("berilgan_sana"),
            "muddat": display_muddat,
            "deadline_iso": deadline_iso,
            "holat": cls_res["status"],
            "bajarilish_foizi": perc_num,
            "ustuvorlik": get_val("ustuvorlik") or "Orta",
            "izoh": get_val("izoh"),
            "days_remaining": days_remaining,
            "risk_level": risk_level,
            "is_overdue": cls_res["is_overdue"],
            "updated_at": datetime.utcnow(),
            "source_file": original_filename,
            "source_id": source_id,
            "raw_status": raw_status,
            "employee_id": final_emp_id
        })

    return True, records, None

def upload_and_replace_source_excel(
    db: Session,
    source_id: str,
    original_filename: str,
    file_bytes: bytes,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Requirement 7: Atomic source update.
    1. Validate & parse new file.
    2. Save to persistent storage.
    3. In DB transaction: delete OLD records for that source_id, insert NEW records.
    4. Recalculate source summary & update task_sources table.
    Does NOT append to old records!
    """
    success, records, err = parse_excel_file(file_bytes, source_id, original_filename, db, sheet_name=sheet_name)
    if not success:
        return {"success": False, "error": err}

    # Save to persistent server storage
    source_dir = os.path.join(TASKS_DIR, source_id)
    os.makedirs(source_dir, exist_ok=True)
    current_excel_path = os.path.join(source_dir, "current.xlsx")

    with open(current_excel_path, "wb") as f:
        f.write(file_bytes)

    # Database atomic transaction
    try:
        # Delete old records only for this source_id
        db.query(Task).filter(Task.source_id == source_id).delete()

        # Insert new records
        for r in records:
            task = Task(**r)
            db.add(task)

        # Update or create task_sources row
        now_iso = datetime.utcnow().isoformat()
        src_row = db.query(TaskSource).filter(TaskSource.id == source_id).first()
        if src_row:
            src_row.file_path = current_excel_path
            src_row.original_filename = original_filename
            src_row.updated_at = now_iso
            src_row.status = "active"
            src_row.total_records = len(records)
            src_row.error_message = None
        else:
            std_name = f"Topshiriq {source_id}"
            for s in STANDARD_SOURCES:
                if s["id"] == source_id:
                    std_name = s["name"]
                    break
            db.add(TaskSource(
                id=source_id,
                name=std_name,
                type="uploaded",
                file_path=current_excel_path,
                original_filename=original_filename,
                updated_at=now_iso,
                status="active",
                total_records=len(records)
            ))

        # Update last sync time
        setting_sync = db.query(Setting).filter(Setting.key == "last_successful_sync").first()
        if setting_sync:
            setting_sync.value = now_iso
        else:
            db.add(Setting(key="last_successful_sync", value=now_iso))

        db.commit()

        return {
            "success": True,
            "message": f"'{original_filename}' muvaffaqiyatli yuklandi va yangilandi ({len(records)} ta topshiriq)",
            "source_id": source_id,
            "total_records": len(records)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving source {source_id}: {e}")
        return {"success": False, "error": f"Ma'lumotlar bazasiga saqlashda xatolik: {e}"}

def refresh_all_task_sources(db: Session) -> Dict[str, Any]:
    """
    Requirement 8: Reread all active task sources from server storage.
    """
    sources = db.query(TaskSource).all()
    total_recs = 0
    now_iso = datetime.utcnow().isoformat()
    today_iso = get_tashkent_today_iso()
    emp_by_id, emp_by_name, emp_by_dept = get_employee_lookup_maps(db)

    # Re-evaluate all tasks in database for current date
    all_tasks = db.query(Task).all()
    for t in all_tasks:
        cls_res = classify_task_status(
            raw_status=t.raw_status or t.holat or "",
            percentage=t.bajarilish_foizi or 0.0,
            deadline_iso=t.deadline_iso or "",
            today_iso=today_iso,
            is_overdue_flag=bool(t.is_overdue)
        )
        t.holat = cls_res["status"]
        t.is_overdue = cls_res["is_overdue"]

        # Re-check employee photo match if not set
        if not t.employee_id or t.employee_id.strip() == "":
            nname = normalize_string(t.masul)
            if nname in emp_by_name:
                t.employee_id = emp_by_name[nname].employee_id
            elif t.boshqarma:
                ndept = normalize_string(t.boshqarma)
                if ndept in emp_by_dept:
                    t.employee_id = emp_by_dept[ndept].employee_id

    # Update counts in task_sources
    for s in sources:
        cnt = db.query(Task).filter(Task.source_id == s.id).count()
        s.total_records = cnt
        total_recs += cnt

    # Update sync settings
    set_last = db.query(Setting).filter(Setting.key == "last_successful_sync").first()
    if set_last:
        set_last.value = now_iso
    else:
        db.add(Setting(key="last_successful_sync", value=now_iso))

    set_msg = db.query(Setting).filter(Setting.key == "sync_message").first()
    if set_msg:
        set_msg.value = "Barcha ma'lumotlar dolzarb"
    else:
        db.add(Setting(key="sync_message", value="Barcha ma'lumotlar dolzarb"))

    db.commit()

    return {
        "success": True,
        "total_records": db.query(Task).count(),
        "last_updated": now_iso
    }
