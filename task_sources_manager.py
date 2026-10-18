import os
import io
import json
import logging
import shutil
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Task, ImportLog
from .universal_excel_parser import (
    parse_single_excel,
    DATA_DIR,
    BASE_DIR
)

logger = logging.getLogger(__name__)

TASKS_DIR = os.path.join(DATA_DIR, "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

# 8 designated task sources
DEFAULT_TASK_SOURCES = [
    {"source_id": f"task_{i}", "name": f"Topshiriq {i}"}
    for i in range(1, 9)
]

def get_task_dir(source_id: str) -> str:
    """Returns absolute directory for a specific task source."""
    d = os.path.join(TASKS_DIR, source_id)
    os.makedirs(d, exist_ok=True)
    return d

def get_task_current_excel_path(source_id: str) -> str:
    """Returns absolute path to current.xlsx for a task."""
    return os.path.join(get_task_dir(source_id), "current.xlsx")

def get_task_meta_path(source_id: str) -> str:
    """Returns absolute path to meta.json for a task."""
    return os.path.join(get_task_dir(source_id), "meta.json")

def read_task_meta(source_id: str, default_name: Optional[str] = None) -> Dict[str, Any]:
    """Reads metadata for a task source."""
    meta_path = get_task_meta_path(source_id)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading meta for {source_id}: {e}")
    
    excel_path = get_task_current_excel_path(source_id)
    has_file = os.path.exists(excel_path)
    
    return {
        "source_id": source_id,
        "name": default_name or f"Topshiriq {source_id.split('_')[-1]}",
        "original_filename": "current.xlsx" if has_file else None,
        "has_file": has_file,
        "uploaded_at": None,
        "total_records": 0
    }

def write_task_meta(source_id: str, meta: Dict[str, Any]):
    """Writes metadata for a task source."""
    meta_path = get_task_meta_path(source_id)
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving meta for {source_id}: {e}")

def calculate_single_task_summary(db: Session, source_id: str) -> Dict[str, Any]:
    """
    Calculates summary metrics for one specific task source (Requirement 5).
    """
    tasks = db.query(Task).filter(Task.source_id == source_id).all()
    total = len(tasks)
    
    if total == 0:
        return {
            "jami_topshiriqlar": 0,
            "bajarilgan": 0,
            "jarayonda": 0,
            "boshlanmagan": 0,
            "muddati_otgan": 0,
            "umumiy_bajarilish_foizi": 0.0,
            "kritik_risk": 0,
            "yuqori_risk": 0,
            "orta_risk": 0,
            "past_risk": 0
        }
    
    bajarilgan = sum(1 for t in tasks if t.holat == "Bajarildi" or t.bajarilish_foizi >= 100.0)
    jarayonda = sum(1 for t in tasks if (t.holat == "Jarayonda" or (0 < t.bajarilish_foizi < 100.0)) and not t.is_overdue and t.holat != "Bajarildi")
    boshlanmagan = sum(1 for t in tasks if t.holat == "Boshlanmagan" and t.bajarilish_foizi == 0.0 and not t.is_overdue)
    muddati_otgan = sum(1 for t in tasks if t.is_overdue or t.holat == "Kechikkan")
    
    kritik_risk = sum(1 for t in tasks if t.risk_level == "Kritik")
    yuqori_risk = sum(1 for t in tasks if t.risk_level == "Yuqori")
    orta_risk = sum(1 for t in tasks if t.risk_level == "O'rta")
    past_risk = sum(1 for t in tasks if t.risk_level == "Past")
    
    avg_foiz = round(sum(t.bajarilish_foizi for t in tasks) / total, 1)
    
    return {
        "jami_topshiriqlar": total,
        "bajarilgan": bajarilgan,
        "jarayonda": jarayonda,
        "boshlanmagan": boshlanmagan,
        "muddati_otgan": muddati_otgan,
        "umumiy_bajarilish_foizi": avg_foiz,
        "kritik_risk": kritik_risk,
        "yuqori_risk": yuqori_risk,
        "orta_risk": orta_risk,
        "past_risk": past_risk
    }

def get_all_task_sources_info(db: Session) -> List[Dict[str, Any]]:
    """
    Returns information and calculated summaries for all 8 task sources.
    """
    results = []
    for item in DEFAULT_TASK_SOURCES:
        sid = item["source_id"]
        meta = read_task_meta(sid, item["name"])
        excel_path = get_task_current_excel_path(sid)
        meta["has_file"] = os.path.exists(excel_path)
        
        # Count actual DB records for this source
        db_count = db.query(Task).filter(Task.source_id == sid).count()
        meta["total_records"] = db_count
        meta["summary"] = calculate_single_task_summary(db, sid)
        results.append(meta)
    return results

def upload_and_replace_task_excel(
    db: Session,
    source_id: str,
    filename: str,
    file_bytes: bytes,
    custom_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Uploads and replaces Excel for one specific task source (Requirements 3, 4, 13, 14).
    
    Transaction-safe replacement workflow:
    1. Validate & Parse new Excel
    2. If validation fails: do NOT touch previous valid Excel or DB records!
    3. If valid:
       - Begin DB transaction
       - Delete old records for THIS task only
       - Insert new records with source_id and source_file
       - Commit
       - Replace current.xlsx on disk
       - Update metadata
       - Recalculate summary
    """
    base_name = os.path.basename(filename)
    dest_dir = get_task_dir(source_id)
    current_excel_path = get_task_current_excel_path(source_id)
    
    # 1. Parse and validate new Excel
    parse_res = parse_single_excel(io.BytesIO(file_bytes), base_name, custom_mapping=custom_mapping)
    
    if parse_res.get("needs_mapping"):
        return {
            "success": False,
            "needs_mapping": True,
            "filename": base_name,
            "source_id": source_id,
            "columns": parse_res.get("columns", []),
            "missing_required": parse_res.get("missing_required", []),
            "error": "Fayl ustunlarini moslashtirish talab etiladi"
        }
        
    if not parse_res.get("success"):
        return {
            "success": False,
            "filename": base_name,
            "source_id": source_id,
            "error": parse_res.get("error", "Excel fayli yaroqsiz")
        }
        
    raw_records = parse_res.get("records", [])
    if not raw_records:
        return {
            "success": False,
            "filename": base_name,
            "source_id": source_id,
            "error": f"'{base_name}' faylida yaroqli topshiriq qatorlari topilmadi"
        }

    # 2. Prepare normalized records for this task
    # Guarantee primary key uniqueness and source attribution
    normalized_records = []
    for idx, r in enumerate(raw_records):
        scoped_id = f"{source_id}_{idx + 1}"
        record_copy = dict(r)
        record_copy["id"] = scoped_id
        record_copy["source_id"] = source_id
        record_copy["source_file"] = base_name
        normalized_records.append(record_copy)

    # 3. Transaction-safe database replacement (Requirement 14)
    # Delete old records for THIS task only, insert new records
    try:
        db.query(Task).filter(Task.source_id == source_id).delete()
        
        task_objs = [Task(**rec) for rec in normalized_records]
        db.bulk_save_objects(task_objs)
        
        now_dt = datetime.now()
        log_entry = ImportLog(
            source_type=f"TASK_SOURCE_{source_id.upper()}",
            import_time=now_dt,
            total_rows=len(normalized_records),
            successful_rows=len(normalized_records),
            error_rows=0,
            file_name=base_name,
            status="SUCCESS",
            message=f"{source_id}: {len(normalized_records)} ta topshiriq yangilandi"
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed while replacing {source_id}: {e}")
        return {
            "success": False,
            "filename": base_name,
            "source_id": source_id,
            "error": f"Baza ma'lumotlarini yangilashda xatolik yuz berdi: {str(e)}"
        }

    # 4. Atomic file replacement on disk (Requirement 9 & 14)
    # Save new Excel as current.xlsx
    temp_excel_path = os.path.join(dest_dir, "temp_upload.xlsx")
    try:
        with open(temp_excel_path, "wb") as f:
            f.write(file_bytes)
            
        if os.path.exists(current_excel_path):
            os.remove(current_excel_path)
            
        os.rename(temp_excel_path, current_excel_path)
    except Exception as e:
        logger.error(f"Error persisting current.xlsx for {source_id}: {e}")
        # DB is committed, but file write had an issue
        if os.path.exists(temp_excel_path):
            try:
                shutil.copy2(temp_excel_path, current_excel_path)
                os.remove(temp_excel_path)
            except Exception:
                pass

    # 5. Update metadata
    meta = read_task_meta(source_id)
    meta["original_filename"] = base_name
    meta["has_file"] = True
    meta["uploaded_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    meta["total_records"] = len(normalized_records)
    write_task_meta(source_id, meta)

    # 6. Calculate new summary
    summary = calculate_single_task_summary(db, source_id)
    meta["summary"] = summary

    return {
        "success": True,
        "source_id": source_id,
        "filename": base_name,
        "synced_count": len(normalized_records),
        "summary": summary,
        "message": f"{meta['name']} ({base_name}) muvaffaqiyatli yuklandi: {len(normalized_records)} ta topshiriq"
    }

def delete_task_source(db: Session, source_id: str) -> Dict[str, Any]:
    """
    Deletes a task source's Excel file and database records (Requirement 11 - O'chirish).
    """
    try:
        # Delete from DB
        deleted_count = db.query(Task).filter(Task.source_id == source_id).delete()
        db.commit()
        
        # Delete Excel from disk
        excel_path = get_task_current_excel_path(source_id)
        if os.path.exists(excel_path):
            os.remove(excel_path)
            
        # Reset metadata
        meta = read_task_meta(source_id)
        meta["original_filename"] = None
        meta["has_file"] = False
        meta["uploaded_at"] = None
        meta["total_records"] = 0
        write_task_meta(source_id, meta)
        
        return {
            "success": True,
            "source_id": source_id,
            "deleted_count": deleted_count,
            "message": f"{meta.get('name', source_id)} ma'lumotlari o'chirildi"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting {source_id}: {e}")
        return {
            "success": False,
            "source_id": source_id,
            "error": f"O'chirishda xatolik yuz berdi: {str(e)}"
        }

def refresh_single_task_source(db: Session, source_id: str) -> Dict[str, Any]:
    """
    Rereads current.xlsx for a specific task source and recalculates (Requirement 11 - Yangilash).
    """
    excel_path = get_task_current_excel_path(source_id)
    if not os.path.exists(excel_path):
        return {
            "success": False,
            "source_id": source_id,
            "error": f"{source_id} uchun hozircha Excel fayli yuklanmagan"
        }
        
    meta = read_task_meta(source_id)
    original_name = meta.get("original_filename") or "current.xlsx"
    
    try:
        with open(excel_path, "rb") as f:
            raw_bytes = f.read()
    except Exception as e:
        return {
            "success": False,
            "source_id": source_id,
            "error": f"Faylni o'qishda xatolik: {str(e)}"
        }
        
    return upload_and_replace_task_excel(db, source_id, original_name, raw_bytes)

def refresh_all_task_sources(db: Session) -> Dict[str, Any]:
    """
    Rereads every active task's current.xlsx, recalculates each task,
    and recalculates Umumiy svod (Requirement 12).
    """
    refreshed_sources = []
    total_records = 0
    errors = []
    
    for item in DEFAULT_TASK_SOURCES:
        sid = item["source_id"]
        excel_path = get_task_current_excel_path(sid)
        if os.path.exists(excel_path):
            res = refresh_single_task_source(db, sid)
            if res.get("success"):
                refreshed_sources.append(sid)
                total_records += res.get("synced_count", 0)
            else:
                errors.append(f"{sid}: {res.get('error')}")
                
    # Also check data/uploads/ or data/main_page/current.xlsx if no task sources yet
    if not refreshed_sources:
        from .universal_excel_parser import refresh_all_local_excels
        legacy_res = refresh_all_local_excels(db)
        return legacy_res
        
    return {
        "success": True,
        "refreshed_sources": refreshed_sources,
        "total_records": total_records,
        "errors": errors,
        "message": f"{len(refreshed_sources)} ta topshiriq manbasi muvaffaqiyatli qayta o'qildi va hisoblandi"
    }
