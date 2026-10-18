from datetime import datetime, date
from typing import Tuple, Optional
import pandas as pd

def parse_date(date_val) -> Optional[date]:
    if pd.isna(date_val) or date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, pd.Timestamp):
        return date_val.date()
    if isinstance(date_val, (int, float)):
        try:
            return pd.to_datetime(date_val, unit='D', origin='1899-12-30').date()
        except Exception:
            pass

    date_str = str(date_val).strip()
    if not date_str:
        return None

    # Try common formats
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y.%m.%d",
        "%d-%m-%Y",
        "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # If pandas can parse it
    try:
        ts = pd.to_datetime(date_str, errors='coerce')
        if not pd.isna(ts):
            return ts.date()
    except Exception:
        pass
    return None

def calculate_task_risk(
    muddat_val,
    holat_str: str,
    foiz_val: float,
    current_date: Optional[date] = None
) -> Tuple[int, str, bool]:
    """
    Calculates:
      - days_remaining: int
      - risk_level: str ("Kritik", "Yuqori", "O'rta", "Past")
      - is_overdue: bool
    """
    if current_date is None:
        current_date = date.today()

    muddat_date = parse_date(muddat_val)
    holat_clean = (holat_str or "").strip().capitalize()
    is_completed = (holat_clean == "Bajarildi") or (foiz_val >= 100.0)

    if muddat_date is None:
        # Fallback if no valid deadline
        return 0, "Past", False

    delta = (muddat_date - current_date).days
    days_remaining = delta

    # If completed, risk is always Past and not overdue
    if is_completed:
        return days_remaining, "Past", False

    # CRITICAL: Deadline has already passed and task is not completed
    if days_remaining < 0:
        return days_remaining, "Kritik", True

    # HIGH: 3 days or less remaining and completion percentage is below 80%
    if days_remaining <= 3 and foiz_val < 80.0:
        return days_remaining, "Yuqori", False

    # MEDIUM: 7 days or less remaining and completion percentage is below 60%
    if days_remaining <= 7 and foiz_val < 60.0:
        return days_remaining, "O'rta", False

    # LOW: Otherwise
    return days_remaining, "Past", False
