"""
Status and Date Classification Module
Adheres strictly to the 4 classification rules in order (Asia/Tashkent timezone):
1. Completed tasks are not currently overdue, even if their deadline has passed.
2. An unfinished task explicitly marked "kechikkan" or "muddati o‘tgan" is overdue.
3. Any other unfinished task with a deadline before today is overdue, even if original status says "jarayonda".
4. An unfinished task with a valid deadline today or later, and no explicit overdue status, is in progress.
"""

from datetime import datetime, timezone, timedelta
import re
from typing import Dict, Any, Optional, Tuple

def get_tashkent_today_iso() -> str:
    """Returns today's calendar date in Asia/Tashkent (UTC+5) as YYYY-MM-DD."""
    tz_tashkent = timezone(timedelta(hours=5))
    return datetime.now(tz_tashkent).strftime("%Y-%m-%d")

def normalize_string(val: Any) -> str:
    """Normalizes string: lowercase, trims, standardizes apostrophes."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    s = re.sub(r"[\u02BB\u02BC\u2018\u2019`ʻʼ']", "'", s)
    s = re.sub(r"\s+", " ", s)
    return s

OVERDUE_STATUSES = {
    'kechikkan', "muddati o'tgan", "muddati otgan", 'overdue', 'kechikdi', 'muddati utgan'
}

IN_PROGRESS_STATUSES = {
    'jarayonda', 'bajarish jarayonida', 'ijroda', 'bajarilmagan',
    'in progress', 'pending', 'bajarilmoqda', 'ijro etilmoqda'
}

COMPLETED_STATUSES = {
    'bajarilgan', 'bajarildi', 'yakunlangan', 'tamomlandi',
    'yakunlandi', 'completed', 'done'
}

UZBEK_MONTHS = {
    'yanvar': 1, 'fevral': 2, 'mart': 3, 'aprel': 4, 'may': 5, 'iyun': 6,
    'iyul': 7, 'avgust': 8, 'sentabr': 9, 'oktabr': 10, 'noyabr': 11, 'dekabr': 12,
    'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
}

def parse_and_validate_date(val: Any) -> Dict[str, Any]:
    """
    Parses varied date representations (Excel serial, ISO, DD.MM.YYYY, DD/MM/YYYY, text dates).
    Returns dict: {"valid": bool, "iso": Optional[str], "display": str}
    """
    if val is None or val == "":
        return {"valid": False, "iso": None, "display": ""}

    if isinstance(val, (datetime,)):
        iso = val.strftime("%Y-%m-%d")
        disp = val.strftime("%d.%m.%Y")
        return {"valid": True, "iso": iso, "display": disp}

    # Excel serial float/int (e.g. 45580)
    if isinstance(val, (int, float)):
        try:
            # Excel base date is roughly 1899-12-30
            d = datetime(1899, 12, 30) + timedelta(days=float(val))
            iso = d.strftime("%Y-%m-%d")
            disp = d.strftime("%d.%m.%Y")
            return {"valid": True, "iso": iso, "display": disp}
        except Exception:
            pass

    s = str(val).strip()

    # YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            iso = f"{y:04d}-{m:02d}-{d:02d}"
            disp = f"{d:02d}.{m:02d}.{y:04d}"
            return {"valid": True, "iso": iso, "display": disp}

    # DD.MM.YYYY or DD/MM/YYYY
    m_dmy = re.match(r"^(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})", s)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            iso = f"{y:04d}-{m:02d}-{d:02d}"
            disp = f"{d:02d}.{m:02d}.{y:04d}"
            return {"valid": True, "iso": iso, "display": disp}

    # Text like "15 oktabr 2026"
    for month_name, m_num in UZBEK_MONTHS.items():
        if month_name in s.lower():
            m_txt = re.search(r"(\d{1,2})\s*[-–—]?\s*" + month_name + r"\s*[-–—]?\s*(\d{4})", s.lower())
            if m_txt:
                d = int(m_txt.group(1))
                y = int(m_txt.group(2))
                iso = f"{y:04d}-{m_num:02d}-{d:02d}"
                disp = f"{d:02d}.{m_num:02d}.{y:04d}"
                return {"valid": True, "iso": iso, "display": disp}

    return {"valid": False, "iso": None, "display": s}

def calculate_days_delayed(deadline_iso: Optional[str], today_iso: Optional[str] = None) -> int:
    """Calculates days delayed if deadline_iso < today_iso."""
    if not today_iso:
        today_iso = get_tashkent_today_iso()
    if not deadline_iso or deadline_iso >= today_iso:
        return 0
    try:
        d1 = datetime.strptime(deadline_iso, "%Y-%m-%d")
        d2 = datetime.strptime(today_iso, "%Y-%m-%d")
        return max(1, (d2 - d1).days)
    except Exception:
        return 1

def classify_task_status(
    raw_status: str = "",
    percentage: float = 0.0,
    deadline_iso: str = "",
    today_iso: Optional[str] = None,
    is_overdue_flag: bool = False
) -> Dict[str, Any]:
    """
    Applies the 4 rules in order:
    Rule 1: Completed
    Rule 2: Explicit overdue
    Rule 3: Deadline < today
    Rule 4: In progress
    """
    if not today_iso:
        today_iso = get_tashkent_today_iso()

    norm = normalize_string(raw_status)
    perc = float(percentage or 0.0)

    # RULE 1: Completed
    if norm in COMPLETED_STATUSES or perc >= 100 or norm in ("bajarildi", "bajarilgan"):
        return {
            "status": "Bajarildi",
            "is_completed": True,
            "is_overdue": False,
            "days_delayed": 0,
            "needs_verification": False,
            "warning": None
        }

    # RULE 2: Explicit overdue
    if norm in OVERDUE_STATUSES or is_overdue_flag:
        days = calculate_days_delayed(deadline_iso, today_iso) if (deadline_iso and deadline_iso < today_iso) else 1
        return {
            "status": "Muddati o‘tgan",
            "is_completed": False,
            "is_overdue": True,
            "days_delayed": days,
            "needs_verification": not bool(deadline_iso),
            "warning": None
        }

    if not deadline_iso:
        return {
            "status": "Tekshirish zarur",
            "is_completed": False,
            "is_overdue": False,
            "days_delayed": 0,
            "needs_verification": True,
            "warning": "Ijro muddati ko'rsatilmagan"
        }

    # RULE 3: Deadline < today
    if deadline_iso < today_iso:
        return {
            "status": "Muddati o‘tgan",
            "is_completed": False,
            "is_overdue": True,
            "days_delayed": calculate_days_delayed(deadline_iso, today_iso),
            "needs_verification": False,
            "warning": None
        }

    # RULE 4: In progress
    return {
        "status": "Bajarish jarayonida",
        "is_completed": False,
        "is_overdue": False,
        "days_delayed": 0,
        "needs_verification": False,
        "warning": None
    }
