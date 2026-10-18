import os
import io
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from .models import Task, ImportLog
from .risk_engine import calculate_task_risk, parse_date

logger = logging.getLogger("main_page_excel_parser")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MAIN_PAGE_DIR = os.path.join(DATA_DIR, "main_page")
MAIN_PAGE_EXCEL_PATH = os.path.join(MAIN_PAGE_DIR, "current.xlsx")

# Required / known header mappings
HEADER_ALIASES = {
    "id": "ID",
    "topshiriq_id": "ID",
    "kod": "ID",
    "raqami": "ID",
    "topshiriq_raqami": "ID",
    "t/r": "ID",
    "tr": "ID",
    "№": "ID",
    "no": "ID",
    "boshqarma": "Boshqarma",
    "boshqarma_nomi": "Boshqarma",
    "department": "Boshqarma",
    "bo'lim": "Boshqarma",
    "bolim": "Boshqarma",
    "tashkilot": "Boshqarma",
    "boshqarma/bo'lim": "Boshqarma",
    "отдел": "Boshqarma",
    "управление": "Boshqarma",
    "topshiriq": "Topshiriq",
    "topshiriq_mazmuni": "Topshiriq",
    "hujjat_nomi": "Topshiriq",
    "task": "Topshiriq",
    "vazifa": "Topshiriq",
    "mazmuni": "Topshiriq",
    "topshiriqlar": "Topshiriq",
    "задание": "Topshiriq",
    "поручение": "Topshiriq",
    "masul": "Masul",
    "mas'ul": "Masul",
    "mas’ul": "Masul",
    "ijrochi": "Masul",
    "masul_shaxs": "Masul",
    "mas'ul_shaxs": "Masul",
    "javobgar": "Masul",
    "ответственный": "Masul",
    "berilgan_sana": "Berilgan_sana",
    "berilgan sana": "Berilgan_sana",
    "boshlanish_sanasi": "Berilgan_sana",
    "sana": "Berilgan_sana",
    "kiruvchi_sana": "Berilgan_sana",
    "дата_выдачи": "Berilgan_sana",
    "muddat": "Muddat",
    "ijro_muddati": "Muddat",
    "oxirgi_muddat": "Muddat",
    "deadline": "Muddat",
    "reja_sanasi": "Muddat",
    "срок": "Muddat",
    "holat": "Holat",
    "status": "Holat",
    "holati": "Holat",
    "ijro_holati": "Holat",
    "статус": "Holat",
    "состояние": "Holat",
    "bajarilish_foizi": "Bajarilish_foizi",
    "bajarilish foizi": "Bajarilish_foizi",
    "bajarilish (%)": "Bajarilish_foizi",
    "bajarilish(%)": "Bajarilish_foizi",
    "foiz": "Bajarilish_foizi",
    "foizi": "Bajarilish_foizi",
    "ijro_foizi": "Bajarilish_foizi",
    "%": "Bajarilish_foizi",
    "процент": "Bajarilish_foizi",
    "ustuvorlik": "Ustuvorlik",
    "priority": "Ustuvorlik",
    "daraja": "Ustuvorlik",
    "приоритет": "Ustuvorlik",
    "izoh": "Izoh",
    "note": "Izoh",
    "izohlar": "Izoh",
    "примечание": "Izoh"
}

def normalize_status(raw_status: Any, percent: float) -> str:
    """Normalizes task status into standard terms: Bajarildi, Jarayonda, Boshlanmagan, Kechikkan."""
    if percent >= 100.0:
        return "Bajarildi"
    
    if raw_status is None or pd.isna(raw_status):
        return "Jarayonda" if percent > 0 else "Boshlanmagan"
    
    s = str(raw_status).strip().lower()
    if s in ["bajarildi", "bajarilgan", "yakunlandi", "tamomlandi", "bajarildi."]:
        return "Bajarildi"
    if s in ["jarayonda", "bajarilmoqda", "amalga oshirilmoqda", "jarayonda."]:
        return "Jarayonda"
    if s in ["boshlanmagan", "kutilmoqda", "yangi", "ochiq", "boshlanmadi"]:
        return "Boshlanmagan"
    if s in ["kechikkan", "muddati o'tgan", "muddati otgan", "muddati_otgan", "kechikmoqda"]:
        return "Kechikkan"
    
    return "Jarayonda" if percent > 0 else "Boshlanmagan"

def normalize_percentage(val: Any) -> float:
    """Safely normalizes percentage into 0.0 - 100.0 float range."""
    if val is None or pd.isna(val):
        return 0.0
    try:
        if isinstance(val, str):
            v_clean = val.replace('%', '').replace(',', '.').strip()
            num = float(v_clean)
        else:
            num = float(val)
        # Handle fractional representation (e.g. 0.85 -> 85%)
        if 0.0 < num <= 1.0:
            num *= 100.0
        return max(0.0, min(100.0, round(num, 1)))
    except (ValueError, TypeError):
        return 0.0

def normalize_priority(val: Any) -> str:
    """Normalizes priority to Yuqori, Orta, Past."""
    if val is None or pd.isna(val):
        return "Orta"
    s = str(val).strip().lower()
    if "yuqori" in s or "high" in s:
        return "Yuqori"
    if "past" in s or "low" in s:
        return "Past"
    return "Orta"

def read_and_parse_main_page_excel(file_source: Any) -> Dict[str, Any]:
    """
    Reads, validates, and parses the Main Page Excel file.
    file_source can be a file path string or bytes/BytesIO.
    Returns parsed records and calculated summary metrics.
    """
    os.makedirs(MAIN_PAGE_DIR, exist_ok=True)
    
    # 1. Load Excel via pandas
    try:
        excel_file = pd.ExcelFile(file_source)
    except Exception as e:
        logger.error(f"Cannot open Excel file: {e}")
        return {
            "success": False,
            "error": f"Excel faylini ochishda xatolik: {str(e)}",
            "records": []
        }
    
    sheet_name = excel_file.sheet_names[0]
    # Check if a sheet named 'Sheet1' or 'Ijro' or similar exists
    for s in excel_file.sheet_names:
        s_lower = s.lower().strip()
        if any(k in s_lower for k in ['sheet1', 'ijro', 'intizom', 'topshiriq', 'bosh sahifa', 'asosiy']):
            sheet_name = s
            break

    # Helper function to check mapping match count
    def get_column_mapping(columns):
        mapping = {}
        for col in columns:
            c_clean = str(col).strip().lower().replace('-', '_').replace(' ', '_').replace("'", "").replace("’", "").replace("`", "")
            if c_clean in HEADER_ALIASES:
                mapping[col] = HEADER_ALIASES[c_clean]
            else:
                for alias_key, target in HEADER_ALIASES.items():
                    alias_clean = alias_key.replace('_', ' ').replace("'", "").replace("’", "")
                    if alias_clean == str(col).strip().lower():
                        mapping[col] = target
                        break
        return mapping

    # Scan the first 5 rows to find the best header row (in case title is in row 0)
    df = None
    best_mapping = {}
    for header_idx in range(5):
        try:
            cand_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_idx)
            cand_mapping = get_column_mapping(cand_df.columns)
            mapped_targets = set(cand_mapping.values())
            if "Topshiriq" in mapped_targets and "Boshqarma" in mapped_targets:
                df = cand_df
                best_mapping = cand_mapping
                break
        except Exception:
            continue

    if df is None:
        # Fallback to default header=0
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        best_mapping = get_column_mapping(df.columns)

    if df.empty:
        return {
            "success": False,
            "error": "Excel faylida ma'lumotlar topilmadi (jadval bo'sh)",
            "records": []
        }

    df = df.rename(columns=best_mapping)

    # Check essential columns
    required = ["Boshqarma", "Topshiriq"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        return {
            "success": False,
            "error": f"Excel faylida majburiy ustunlar yetishmaydi: {', '.join(missing)} (Mavjud ustunlar: {', '.join(str(c) for c in df.columns[:8])})",
            "records": []
        }
        
    records = []
    today = date.today()
    
    for idx, row in df.iterrows():
        topshiriq_val = row.get("Topshiriq")
        if pd.isna(topshiriq_val) or not str(topshiriq_val).strip():
            continue  # Skip empty task rows
            
        task_id = str(row.get("ID") or f"TASK-{idx + 101}").strip()
        boshqarma = str(row.get("Boshqarma") or "Boshqarma").strip()
        topshiriq = str(topshiriq_val).strip()
        masul = str(row.get("Masul") or "Mas'ul biriktirilmagan").strip()
        
        # Parse Dates
        berilgan_sana_date = parse_date(row.get("Berilgan_sana"))
        berilgan_sana_str = berilgan_sana_date.strftime("%Y-%m-%d") if berilgan_sana_date else None
        
        muddat_date = parse_date(row.get("Muddat"))
        if muddat_date:
            muddat_str = muddat_date.strftime("%Y-%m-%d")
        else:
            muddat_str = (today).strftime("%Y-%m-%d")
            muddat_date = today
            
        # Parse & Normalize percentage and status
        foiz = normalize_percentage(row.get("Bajarilish_foizi"))
        holat = normalize_status(row.get("Holat"), foiz)
        ustuvorlik = normalize_priority(row.get("Ustuvorlik"))
        izoh = str(row.get("Izoh")).strip() if pd.notna(row.get("Izoh")) else ""
        
        # Calculate Overdue, Days Remaining & Risk
        days_rem, risk_level, is_overdue = calculate_task_risk(
            muddat_val=muddat_date,
            holat_str=holat,
            foiz_val=foiz,
            current_date=today
        )
        
        # If status was explicitly Kechikkan, ensure is_overdue is True
        if holat == "Kechikkan" and foiz < 100.0:
            is_overdue = True
            if risk_level == "Past":
                risk_level = "Yuqori"
                
        records.append({
            "id": task_id,
            "boshqarma": boshqarma,
            "topshiriq": topshiriq,
            "masul": masul,
            "berilgan_sana": berilgan_sana_str,
            "muddat": muddat_str,
            "holat": holat,
            "bajarilish_foizi": foiz,
            "ustuvorlik": ustuvorlik,
            "izoh": izoh,
            "days_remaining": days_rem,
            "risk_level": risk_level,
            "is_overdue": is_overdue
        })
        
    if not records:
        return {
            "success": False,
            "error": "Excel faylida yaroqli topshiriqlar qatorlari topilmadi",
            "records": []
        }
        
    return {
        "success": True,
        "total_parsed": len(records),
        "records": records
    }

def sync_main_page_to_database(db: Session, records: List[Dict[str, Any]], filename: str = "current.xlsx") -> Dict[str, Any]:
    """
    Synchronizes parsed main page records into SQLite using a safe transaction.
    Rolls back on error to ensure previous valid data is preserved.
    """
    now_dt = datetime.now()
    
    try:
        # Atomic replace inside database session
        db.query(Task).delete()
        
        tasks_to_insert = [Task(**rec) for rec in records]
        db.bulk_save_objects(tasks_to_insert)
        
        # Log successful import
        log_entry = ImportLog(
            source_type="MAIN_PAGE",
            import_time=now_dt,
            total_rows=len(records),
            successful_rows=len(records),
            error_rows=0,
            file_name=filename,
            status="SUCCESS",
            message=f"{len(records)} ta topshiriq muvaffaqiyatli sinxronlashtirildi"
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Main Page Excel successfully synchronized with {len(records)} tasks.")
        return {
            "success": True,
            "synced_count": len(records),
            "last_updated": now_dt.strftime("%d.%m.%Y %H:%M:%S"),
            "message": "Ma'lumotlar muvaffaqiyatli yangilandi"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error synchronizing main page tasks to DB: {e}")
        # Log failure
        try:
            err_log = ImportLog(
                source_type="MAIN_PAGE",
                import_time=now_dt,
                total_rows=len(records),
                successful_rows=0,
                error_rows=len(records),
                file_name=filename,
                status="ERROR",
                message=f"Bazaga yozishda xatolik: {str(e)}"
            )
            db.add(err_log)
            db.commit()
        except Exception:
            db.rollback()
            
        return {
            "success": False,
            "error": f"1-sahifa Excel ma'lumotlarini o'qishda xatolik yuz berdi: {str(e)}"
        }

def process_and_sync_main_page(db: Session, file_path_or_bytes: Optional[Any] = None, save_as_current: bool = False, original_filename: str = "current.xlsx") -> Dict[str, Any]:
    """
    Complete pipeline: Reads -> Validates -> Normalizes -> Calculates -> Syncs to SQLite.
    Saves working copy to data/main_page/current.xlsx if requested.
    """
    os.makedirs(MAIN_PAGE_DIR, exist_ok=True)
    
    raw_bytes_to_save = None
    if file_path_or_bytes is None:
        file_path_or_bytes = MAIN_PAGE_EXCEL_PATH
        if not os.path.exists(MAIN_PAGE_EXCEL_PATH):
            ijro_fallback = os.path.join(DATA_DIR, "ijro.xlsx")
            if os.path.exists(ijro_fallback):
                file_path_or_bytes = ijro_fallback
            else:
                return {
                    "success": False,
                    "error": "1-sahifa uchun Excel fayli (data/main_page/current.xlsx) topilmadi"
                }
    elif isinstance(file_path_or_bytes, (bytes, bytearray)):
        raw_bytes_to_save = file_path_or_bytes
        file_path_or_bytes = io.BytesIO(file_path_or_bytes)
        
    parse_res = read_and_parse_main_page_excel(file_path_or_bytes)
    if not parse_res["success"]:
        return {
            "success": False,
            "error": parse_res.get("error", "1-sahifa Excel ma'lumotlarini o'qishda xatolik yuz berdi")
        }

    # If parsing succeeded and saving was requested, write to disk
    if save_as_current and raw_bytes_to_save is not None:
        try:
            with open(MAIN_PAGE_EXCEL_PATH, "wb") as f:
                f.write(raw_bytes_to_save)
            ijro_path = os.path.join(DATA_DIR, "ijro.xlsx")
            with open(ijro_path, "wb") as f:
                f.write(raw_bytes_to_save)
            logger.info("Successfully saved uploaded Excel to current.xlsx and ijro.xlsx")
        except Exception as e:
            logger.warning(f"Could not write Excel copy to disk: {e}")
        
    sync_res = sync_main_page_to_database(db, parse_res["records"], filename=original_filename)
    if not sync_res["success"]:
        return sync_res
        
    return {
        "success": True,
        "total_records": parse_res["total_parsed"],
        "last_updated": sync_res["last_updated"],
        "message": f"{parse_res['total_parsed']} ta topshiriq muvaffaqiyatli qabul qilindi va yangilandi"
    }
