import os
import re
import io
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from .models import Task, ImportLog
from .risk_engine import calculate_task_risk, parse_date

logger = logging.getLogger("universal_excel_parser")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
MAPPINGS_FILE = os.path.join(DATA_DIR, "column_mappings.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)

# Canonical field names
CANONICAL_FIELDS = [
    "ID",
    "Boshqarma",
    "Topshiriq",
    "Masul",
    "Berilgan_sana",
    "Muddat",
    "Holat",
    "Bajarilish_foizi",
    "Ustuvorlik",
    "Izoh"
]

# Comprehensive alias dictionary across Uzbek (Latin/Cyrillic), Russian, and English
HEADER_SYNONYMS: Dict[str, List[str]] = {
    "ID": [
        "id", "topshiriq_id", "kod", "raqami", "topshiriq_raqami", "t/r", "tr", "№", "no", 
        "tartib_raqami", "номер", "№_п/п", "п/п", "ид", "number", "code", "item_no", "nomer",
        "т/р", "тр", "тартиб_рақами"
    ],
    "Boshqarma": [
        "boshqarma", "boshqarma_nomi", "bolim", "bo'lim", "bo‘lim", "tashkilot", "idora", 
        "departament", "tarkibiy_tuzilma", "tuzilma", "boshqarma/bo'lim", "department", 
        "dept", "division", "organization", "unit", "управление", "отдел", "департамент", 
        "подразделение", "организация", "ведомство",
        "бошқарма", "бошкарма", "бошқарма_номи", "бўлим", "булим", "тузилма", "идора", "ташкилот"
    ],
    "Topshiriq": [
        "topshiriq", "topshiriq_nomi", "topshiriq_mazmuni", "hujjat_nomi", "vazifa", 
        "mazmuni", "mazmun", "topshiriqlar", "masalalar", "band", "band_mazmuni", "hujjat", 
        "task", "task_name", "task_description", "assignment", "subject", "content", 
        "поручение", "задание", "задача", "документ", "содержание", "наименование_поручения", 
        "суть", "вопрос", "наименование", "пункт", "краткое_содержание",
        "топшириқ", "топширик", "топшириқ_номи", "вазифа", "мазмуни", "мазмун", "ҳужжат", "хужжат", "ҳужжат_номи", "банд"
    ],
    "Masul": [
        "masul", "mas'ul", "mas’ul", "masul_shaxs", "mas'ul_shaxs", "ijrochi", "javobgar", 
        "bajaruvchi", "xodim", "masullar", "responsible", "assignee", "executor", "owner", 
        "person", "исполнитель", "ответственный", "отв_исполнитель", "фио", 
        "ответственный_сотрудник", "соисполнитель", "ответственное_лицо",
        "масъул", "масул", "масъул_шахс", "ижрочи", "жавобгар", "бажарувчи", "ходим"
    ],
    "Berilgan_sana": [
        "berilgan_sana", "berilgan sana", "boshlanish_sanasi", "kiruvchi_sana", "sana", 
        "ro'yxat_sanasi", "sanasi", "start_date", "assigned_date", "created_at", "date", 
        "дата_выдачи", "дата_поручения", "дата_регистрации", "дата_поступления", "дата",
        "берилган_сана", "сана", "бошланиш_санаси", "рўйхат_санаси"
    ],
    "Muddat": [
        "muddat", "ijro_muddati", "oxirgi_muddat", "deadline", "reja_sanasi", "bajarish_muddati", 
        "tugash_sanasi", "due_date", "target_date", "finish_date", "срок", "срок_исполнения", 
        "дата_исполнения", "дедлайн", "плановый_срок", "конечный_срок",
        "муддат", "ижро_муддати", "охирги_муддат", "бажариш_муддати", "тугаш_санаси"
    ],
    "Holat": [
        "holat", "status", "holati", "ijro_holati", "vaziyat", "state", "condition", 
        "статус", "состояние", "статус_исполнения", "отметка",
        "ҳолат", "холат", "ҳолати", "холати", "ижро_ҳолати"
    ],
    "Bajarilish_foizi": [
        "bajarilish_foizi", "bajarilish foizi", "bajarilish (%)", "bajarilish(%)", "foiz", 
        "foizi", "ijro_foizi", "bajarilishi", "foizda", "%", "percent", "percentage", 
        "progress", "completion_%", "процент", "процент_исполнения", "процент_выполнения", 
        "выполнение_%", "%_выполнения", "доля", "выполнение",
        "бажарилиш_фоизи", "бажарилиши", "фоиз", "фоизи", "ижро_фоизи", "бажариш_фоизи"
    ],
    "Ustuvorlik": [
        "ustuvorlik", "daraja", "ahamiyat", "muhimlik", "priority", "urgency", "level", 
        "приоритет", "важность", "срочность",
        "устуворлик", "даража", "муҳимлик", "мухимлик", "аҳамият", "ахамият"
    ],
    "Izoh": [
        "izoh", "izohlar", "eslatma", "natija", "sabab", "note", "comment", "remarks", 
        "info", "примечание", "комментарий", "заметка",
        "изоҳ", "изох", "изоҳлар", "эслатма", "натижа", "сабаб"
    ]
}

# Inverted mapping: cleaned_alias -> canonical field
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canon, aliases in HEADER_SYNONYMS.items():
    for alias in aliases:
        clean = alias.strip().lower().replace('-', '_').replace(' ', '_').replace("'", "").replace("’", "").replace("`", "")
        ALIAS_TO_CANONICAL[clean] = canon


def clean_col_name(col: Any) -> str:
    """Normalize string column name for matching."""
    s = str(col).strip().lower()
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"['’`\"]", "", s)
    s = re.sub(r"[\s\-_/]+", "_", s)
    return s.strip("_")


def load_saved_mappings() -> Dict[str, Dict[str, str]]:
    """Loads custom saved column mappings from JSON file."""
    if not os.path.exists(MAPPINGS_FILE):
        return {}
    try:
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("mappings", {})
    except Exception as e:
        logger.warning(f"Could not load column mappings: {e}")
        return {}


def save_column_mapping(filename: str, mapping: Dict[str, str]):
    """Saves a column mapping for a given file name."""
    existing = load_saved_mappings()
    base_name = os.path.basename(filename)
    existing[base_name] = mapping
    try:
        with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mappings": existing}, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved custom column mapping for {base_name}")
    except Exception as e:
        logger.error(f"Failed to save custom column mapping: {e}")


def extract_cell_value(val: Any) -> Any:
    """Extracts a scalar value from a cell, handling pandas Series if duplicates occurred."""
    if isinstance(val, (pd.Series, list)):
        if len(val) == 0:
            return None
        return val.iloc[0] if hasattr(val, 'iloc') else val[0]
    return val


def normalize_status_value(raw_status: Any, percent: float) -> str:
    """Normalizes task status into: Bajarildi, Jarayonda, Boshlanmagan, Kechikkan."""
    raw_status = extract_cell_value(raw_status)
    if percent >= 100.0:
        return "Bajarildi"
    
    if raw_status is None or pd.isna(raw_status):
        return "Jarayonda" if percent > 0 else "Boshlanmagan"
    
    s = str(raw_status).strip().lower()
    if any(k in s for k in [
        "bajarildi", "bajarilgan", "yakunlandi", "tamomlandi", "done", "completed", "выполнен", "исполнен",
        "бажарилди", "бажарилган", "якунланди", "тамомланди"
    ]):
        return "Bajarildi"
    if any(k in s for k in [
        "kechikkan", "muddati o'tgan", "muddati otgan", "просрочен", "overdue",
        "кечиккан", "муддати ўтган", "муддати утган"
    ]):
        return "Kechikkan"
    if any(k in s for k in [
        "jarayonda", "bajarilmoqda", "amalga oshirilmoqda", "in progress", "в процессе", "исполняется",
        "жараёнда", "бажарилмоқда", "амалга оширилмоқда"
    ]):
        return "Jarayonda"
    if any(k in s for k in [
        "boshlanmagan", "kutilmoqda", "yangi", "ochiq", "not started", "не начато",
        "бошланмаган", "кутилмоқда", "янги", "очиқ"
    ]):
        return "Boshlanmagan"
    
    return "Jarayonda" if percent > 0 else "Boshlanmagan"


def normalize_percentage_value(val: Any) -> float:
    """Safely normalizes percentage into 0.0 - 100.0 float range."""
    val = extract_cell_value(val)
    if val is None or pd.isna(val):
        return 0.0
    try:
        if isinstance(val, str):
            v_clean = val.replace('%', '').replace(',', '.').strip()
            num = float(v_clean)
        else:
            num = float(val)
        if 0.0 < num <= 1.0:
            num *= 100.0
        return max(0.0, min(100.0, round(num, 1)))
    except (ValueError, TypeError):
        return 0.0


def normalize_priority_value(val: Any) -> str:
    """Normalizes priority to Yuqori, Orta, Past."""
    val = extract_cell_value(val)
    if val is None or pd.isna(val):
        return "Orta"
    s = str(val).strip().lower()
    if any(k in s for k in ["yuqori", "high", "критич", "высок", "юқори", "юкори"]):
        return "Yuqori"
    if any(k in s for k in ["past", "low", "низк", "паст"]):
        return "Past"
    return "Orta"


def is_summary_row(row_dict: Dict[str, Any]) -> bool:
    """
    Checks if a row is a summary/total row (e.g. Jami, Итого, Всего, Total)
    which must NOT be counted as an individual task.
    """
    summary_words = ["jami", "итого", "всего", "total", "summary", "umumiy", "itogo"]
    
    for field in ["Topshiriq", "Boshqarma", "Masul", "ID"]:
        cell_val = extract_cell_value(row_dict.get(field))
        val = str(cell_val or "").strip().lower()
        if not val or val == "nan":
            continue
        if val in summary_words:
            return True
        for w in summary_words:
            if val.startswith(w + ":") or val.startswith(w + " ") or val == w:
                return True
                
    # If Topshiriq is empty and Boshqarma contains summary word
    boshqarma_val = str(extract_cell_value(row_dict.get("Boshqarma")) or "").strip().lower()
    topshiriq_val = str(extract_cell_value(row_dict.get("Topshiriq")) or "").strip()
    if any(w in boshqarma_val for w in summary_words) and (not topshiriq_val or topshiriq_val == "nan"):
        return True

    return False


def detect_columns(columns: List[Any], custom_mapping: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, str], List[str]]:
    """
    Detects canonical fields for the given raw column names.
    Returns (raw_col -> canonical_field, list of missing essential fields).
    """
    mapping = {}
    detected_canonicals = set()
    
    # 1. Apply custom mapping if provided
    if custom_mapping:
        for raw_col in columns:
            col_str = str(raw_col).strip()
            # If raw_col was mapped directly to a canonical field
            if col_str in custom_mapping and custom_mapping[col_str] in CANONICAL_FIELDS:
                canon = custom_mapping[col_str]
                if canon not in detected_canonicals:
                    mapping[raw_col] = canon
                    detected_canonicals.add(canon)
            # If canonical was mapped to a raw column
            for canon_key, mapped_raw in custom_mapping.items():
                if canon_key in CANONICAL_FIELDS and mapped_raw == col_str and canon_key not in detected_canonicals:
                    mapping[raw_col] = canon_key
                    detected_canonicals.add(canon_key)

    # 2. Automated detection using synonym dictionary
    for raw_col in columns:
        if raw_col in mapping:
            continue
        col_clean = clean_col_name(raw_col)
        if not col_clean:
            continue
            
        # Direct clean match
        if col_clean in ALIAS_TO_CANONICAL:
            canon = ALIAS_TO_CANONICAL[col_clean]
            if canon not in detected_canonicals:
                mapping[raw_col] = canon
                detected_canonicals.add(canon)
                continue
                
        # Substring / partial match
        for alias_clean, canon in ALIAS_TO_CANONICAL.items():
            if alias_clean in col_clean or col_clean in alias_clean:
                if canon not in detected_canonicals:
                    mapping[raw_col] = canon
                    detected_canonicals.add(canon)
                    break

    # Required fields for valid task data
    required = ["Topshiriq", "Boshqarma"]
    missing = [req for req in required if req not in detected_canonicals]
    return mapping, missing


def parse_single_excel(
    file_source: Any,
    filename: str,
    custom_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Parses a single Excel file with dynamic sheet selection, header row detection,
    and automatic column recognition. Returns normalized tasks or column mapping request.
    """
    saved_mappings = load_saved_mappings()
    base_name = os.path.basename(filename)
    active_mapping = custom_mapping or saved_mappings.get(base_name)

    try:
        excel_file = pd.ExcelFile(file_source)
    except Exception as e:
        return {
            "success": False,
            "filename": base_name,
            "error": f"Excel faylini ochishda xatolik: {str(e)}",
            "records": []
        }

    best_df = None
    best_mapping = {}
    best_score = -1
    best_sheet = excel_file.sheet_names[0]
    best_missing = ["Topshiriq", "Boshqarma"]
    best_raw_columns = []

    # Iterate through sheets and candidate header rows (0 to 10)
    for sheet in excel_file.sheet_names:
        for header_idx in range(10):
            try:
                cand_df = pd.read_excel(excel_file, sheet_name=sheet, header=header_idx)
                if cand_df.empty or len(cand_df.columns) < 2:
                    continue
                mapping, missing = detect_columns(cand_df.columns, active_mapping)
                mapped_fields = set(mapping.values())
                
                # Weighting: essential fields give highest weight
                score = 0
                if "Topshiriq" in mapped_fields: score += 15
                if "Boshqarma" in mapped_fields: score += 15
                if "Masul" in mapped_fields: score += 5
                if "Muddat" in mapped_fields: score += 5
                if "Holat" in mapped_fields: score += 3
                if "Bajarilish_foizi" in mapped_fields: score += 3
                if "Ustuvorlik" in mapped_fields: score += 2
                if "ID" in mapped_fields: score += 1
                
                if score > best_score:
                    best_score = score
                    best_df = cand_df
                    best_mapping = mapping
                    best_sheet = sheet
                    best_missing = missing
                    best_raw_columns = [str(c).strip() for c in cand_df.columns if str(c).strip() and not str(c).startswith("Unnamed")]
                    
                    if len(missing) == 0 and score >= 30:
                        break
            except Exception:
                continue
        if best_score >= 35:
            break

    # If essential columns could not be mapped
    if best_df is None or ("Topshiriq" not in best_mapping.values() or "Boshqarma" not in best_mapping.values()):
        # Try fallback: if we have candidate columns, request manual column mapping!
        raw_cols = best_raw_columns or (list(best_df.columns) if best_df is not None else [])
        return {
            "success": False,
            "needs_mapping": True,
            "filename": base_name,
            "available_columns": [str(c) for c in raw_cols],
            "detected_mapping": {str(k): v for k, v in best_mapping.items()},
            "missing_fields": best_missing,
            "error": f"'{base_name}' faylida kerakli ustunlar (Boshqarma, Topshiriq) aniqlanmadi. Iltimos ustunlarni moslashtiring.",
            "records": []
        }

    # Rename mapped columns and deduplicate
    df = best_df.rename(columns=best_mapping)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    records = []
    today = date.today()
    file_slug = re.sub(r'[^a-zA-Z0-9]', '_', base_name).strip('_')[:20]

    for idx, row in df.iterrows():
        topshiriq_val = extract_cell_value(row.get("Topshiriq"))
        if topshiriq_val is None or pd.isna(topshiriq_val) or not str(topshiriq_val).strip():
            continue
            
        row_dict = {
            "ID": extract_cell_value(row.get("ID")),
            "Topshiriq": topshiriq_val,
            "Boshqarma": extract_cell_value(row.get("Boshqarma")),
            "Masul": extract_cell_value(row.get("Masul")),
        }
        
        if is_summary_row(row_dict):
            logger.info(f"Filtered out summary row in {base_name}: {topshiriq_val}")
            continue

        raw_id = extract_cell_value(row.get("ID"))
        task_id = str(raw_id).strip() if (raw_id is not None and pd.notna(raw_id) and str(raw_id).strip()) else f"{idx + 1}"
        scoped_id = f"{file_slug}_{task_id}"

        boshqarma = str(extract_cell_value(row.get("Boshqarma")) or "Boshqarma").strip()
        topshiriq = str(topshiriq_val).strip()
        masul = str(extract_cell_value(row.get("Masul")) or "Mas'ul biriktirilmagan").strip()

        # Dates
        berilgan_sana_date = parse_date(extract_cell_value(row.get("Berilgan_sana")))
        berilgan_sana_str = berilgan_sana_date.strftime("%Y-%m-%d") if berilgan_sana_date else None

        muddat_date = parse_date(extract_cell_value(row.get("Muddat")))
        if muddat_date:
            muddat_str = muddat_date.strftime("%Y-%m-%d")
        else:
            muddat_str = today.strftime("%Y-%m-%d")
            muddat_date = today

        # Percentage, Status, Priority
        foiz = normalize_percentage_value(extract_cell_value(row.get("Bajarilish_foizi")))
        holat = normalize_status_value(extract_cell_value(row.get("Holat")), foiz)
        ustuvorlik = normalize_priority_value(extract_cell_value(row.get("Ustuvorlik")))
        izoh_val = extract_cell_value(row.get("Izoh"))
        izoh = str(izoh_val).strip() if (izoh_val is not None and pd.notna(izoh_val)) else ""

        # Overdue & Risk calculation
        # Rule 6: deadline < today AND task is not completed
        is_completed = (holat == "Bajarildi") or (foiz >= 100.0)
        days_rem, risk_level, is_overdue = calculate_task_risk(
            muddat_val=muddat_date,
            holat_str=holat,
            foiz_val=foiz,
            current_date=today
        )

        # Ensure strict adherence to requirement 6:
        # deadline < today and not completed -> is_overdue = True, Kritik risk
        if not is_completed and muddat_date < today:
            is_overdue = True
            risk_level = "Kritik"
            if holat not in ["Jarayonda", "Boshlanmagan"]:
                holat = "Kechikkan"

        records.append({
            "id": scoped_id,
            "source_file": base_name,
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
            "filename": base_name,
            "error": f"'{base_name}' faylida yaroqli topshiriq qatorlari topilmadi",
            "records": []
        }

    return {
        "success": True,
        "filename": base_name,
        "total_parsed": len(records),
        "records": records
    }


def sync_records_to_database(db: Session, filename: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synchronizes tasks from a single Excel file to SQLite.
    Prevents duplicates by atomically replacing records for THIS source_file only.
    Preserves all records from other source files.
    """
    now_dt = datetime.now()
    base_name = os.path.basename(filename)
    
    try:
        # Remove only existing records belonging to this source_file
        db.query(Task).filter(Task.source_file == base_name).delete()
        
        tasks_to_insert = [Task(**rec) for rec in records]
        db.bulk_save_objects(tasks_to_insert)
        
        log_entry = ImportLog(
            source_type="MULTI_EXCEL",
            import_time=now_dt,
            total_rows=len(records),
            successful_rows=len(records),
            error_rows=0,
            file_name=base_name,
            status="SUCCESS",
            message=f"{len(records)} ta topshiriq muvaffaqiyatli sinxronlashtirildi"
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "success": True,
            "filename": base_name,
            "synced_count": len(records),
            "last_updated": now_dt.strftime("%d.%m.%Y %H:%M:%S")
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving records from {base_name} to database: {e}")
        return {
            "success": False,
            "filename": base_name,
            "error": f"Bazaga yozishda xatolik: {str(e)}"
        }


def process_multiple_excel_files(
    db: Session,
    files_data: List[Tuple[str, bytes]],
    custom_mappings: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Processes multiple Excel files (7-8+ files simultaneously).
    If 7 files are valid and 1 has an error: updates the 7 valid files
    and keeps the previous valid data for the failed file (Requirement 15).
    """
    results = {
        "success": True,
        "processed_files": [],
        "failed_files": [],
        "needs_mapping_files": [],
        "total_imported_records": 0,
        "message": ""
    }
    
    for filename, raw_bytes in files_data:
        base_name = os.path.basename(filename)
        # 1. Save uploaded file locally in data/uploads/ (Requirement 12)
        local_path = os.path.join(UPLOADS_DIR, base_name)
        try:
            with open(local_path, "wb") as f:
                f.write(raw_bytes)
        except Exception as e:
            logger.warning(f"Could not persist {base_name} locally: {e}")

        # 2. Parse file
        f_mapping = (custom_mappings or {}).get(base_name)
        parse_res = parse_single_excel(io.BytesIO(raw_bytes), base_name, custom_mapping=f_mapping)
        
        if parse_res.get("needs_mapping"):
            results["needs_mapping_files"].append(parse_res)
            # Do NOT touch previous data for this file
            continue
            
        if not parse_res.get("success"):
            results["failed_files"].append({
                "filename": base_name,
                "error": parse_res.get("error", "Format xatosi")
            })
            # Do NOT touch previous data for this file
            continue
            
        # 3. Synchronize this file's records to DB
        sync_res = sync_records_to_database(db, base_name, parse_res["records"])
        if sync_res.get("success"):
            results["processed_files"].append({
                "filename": base_name,
                "count": sync_res["synced_count"]
            })
            results["total_imported_records"] += sync_res["synced_count"]
        else:
            results["failed_files"].append({
                "filename": base_name,
                "error": sync_res.get("error")
            })

    total_uploaded = len(files_data)
    processed_count = len(results["processed_files"])
    failed_count = len(results["failed_files"])
    mapping_count = len(results["needs_mapping_files"])

    if processed_count == total_uploaded:
        results["message"] = f"Barcha {processed_count} ta Excel fayli muvaffaqiyatli qabul qilindi ({results['total_imported_records']} ta topshiriq)"
    else:
        results["message"] = f"{processed_count} ta fayl muvaffaqiyatli yangilandi"
        if mapping_count > 0:
            results["message"] += f", {mapping_count} ta fayl uchun ustunlarni moslashtirish talab etiladi"
        if failed_count > 0:
            results["message"] += f", {failed_count} ta faylda xatolik aniqlandi (avvalgi ma'lumotlar saqlab qolindi)"

    return results


def refresh_all_local_excels(db: Session) -> Dict[str, Any]:
    """
    Rereads all Excel files currently stored in data/uploads/ (and main_page/current.xlsx if present),
    recalculates all data, synchronizes the database, and refreshes all metrics (Requirement 13).
    """
    files_to_sync: List[Tuple[str, bytes]] = []
    
    # 1. Collect all files from data/uploads/
    if os.path.exists(UPLOADS_DIR):
        for fname in os.listdir(UPLOADS_DIR):
            if fname.lower().endswith((".xlsx", ".xls")) and not fname.startswith("~$"):
                fpath = os.path.join(UPLOADS_DIR, fname)
                try:
                    with open(fpath, "rb") as f:
                        files_to_sync.append((fname, f.read()))
                except Exception as e:
                    logger.warning(f"Could not read upload file {fname}: {e}")

    # 2. If uploads folder is empty, fallback to data/main_page/current.xlsx or data/ijro.xlsx
    if not files_to_sync:
        main_page_path = os.path.join(DATA_DIR, "main_page", "current.xlsx")
        ijro_path = os.path.join(DATA_DIR, "ijro.xlsx")
        fallback_path = main_page_path if os.path.exists(main_page_path) else (ijro_path if os.path.exists(ijro_path) else None)
        if fallback_path:
            with open(fallback_path, "rb") as f:
                files_to_sync.append((os.path.basename(fallback_path), f.read()))

    if not files_to_sync:
        return {
            "success": False,
            "message": "Yangilash uchun birorta ham Excel fayli topilmadi"
        }

    return process_multiple_excel_files(db, files_to_sync)
