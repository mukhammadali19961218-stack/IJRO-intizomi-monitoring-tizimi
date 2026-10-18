import os
import time
import logging
from datetime import datetime, date, timedelta
import pandas as pd
from sqlalchemy.orm import Session

from .models import Task, ImportLog
from .risk_engine import calculate_task_risk, parse_date

logger = logging.getLogger("excel_reader")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXCEL_PATH = os.path.join(DATA_DIR, "ijro.xlsx")

REQUIRED_COLUMNS = [
    "ID", "Boshqarma", "Topshiriq", "Masul", "Berilgan_sana",
    "Muddat", "Holat", "Bajarilish_foizi", "Ustuvorlik", "Izoh"
]

def create_sample_excel_if_missing():
    """Generates a rich, realistic sample ijro.xlsx if not present."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(EXCEL_PATH):
        return

    today = date.today()

    def d_str(offset_days):
        return (today + timedelta(days=offset_days)).strftime("%Y-%m-%d")

    sample_tasks = [
        # Moliya boshqarmasi
        {
            "ID": "MB-101",
            "Boshqarma": "Moliya boshqarmasi",
            "Topshiriq": "2026-yil 3-chorak moliyaviy hisobotini Vazirlar Mahkamasiga taqdim etish",
            "Masul": "Olimov Rustam",
            "Berilgan_sana": d_str(-30),
            "Muddat": d_str(-2),  # Overdue -> Kritik
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 70.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Hisob-kitoblar yakunlanmoqda"
        },
        {
            "ID": "MB-102",
            "Boshqarma": "Moliya boshqarmasi",
            "Topshiriq": "Investitsiya dasturlari bo'yicha sarflangan mablag'lar auditi",
            "Masul": "Karimov Sardor",
            "Berilgan_sana": d_str(-15),
            "Muddat": d_str(2),   # <= 3 days, foiz < 80 -> Yuqori risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 45.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Audit xulosasi kutilmoqda"
        },
        {
            "ID": "MB-103",
            "Boshqarma": "Moliya boshqarmasi",
            "Topshiriq": "Ish haqi va mukofot pullari to'lov fondini qayta ko'rib chiqish",
            "Masul": "Zokirova Nilufar",
            "Berilgan_sana": d_str(-20),
            "Muddat": d_str(-5),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Orta",
            "Izoh": "To'liq tasdiqlandi"
        },
        {
            "ID": "MB-104",
            "Boshqarma": "Moliya boshqarmasi",
            "Topshiriq": "2027-yilgi yillik budjet rejasining dastlabki loyihasini ishlab chiqish",
            "Masul": "Olimov Rustam",
            "Berilgan_sana": d_str(-5),
            "Muddat": d_str(25),
            "Holat": "Boshlanmagan",
            "Bajarilish_foizi": 0.0,
            "Ustuvorlik": "Past",
            "Izoh": "Kadrlar takliflari kutilmoqda"
        },

        # AKT boshqarmasi
        {
            "ID": "AKT-201",
            "Boshqarma": "AKT boshqarmasi",
            "Topshiriq": "Yagona ijro intizomi avtomatlashtirilgan monitoring tizimini serverga o'rnatish",
            "Masul": "Axmedov Bobur",
            "Berilgan_sana": d_str(-14),
            "Muddat": d_str(1),   # <= 3 days, foiz < 80 -> Yuqori risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 60.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Xavfsizlik testi davom etmoqda"
        },
        {
            "ID": "AKT-202",
            "Boshqarma": "AKT boshqarmasi",
            "Topshiriq": "Barcha stansiyalarda optik tolali aloqa liniyalarini modernizatsiya qilish",
            "Masul": "Tursunov Jamshid",
            "Berilgan_sana": d_str(-40),
            "Muddat": d_str(-10), # Overdue -> Kritik
            "Holat": "Kechikkan",
            "Bajarilish_foizi": 50.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Uskunalar yetkazib berish kechikmoqda"
        },
        {
            "ID": "AKT-203",
            "Boshqarma": "AKT boshqarmasi",
            "Topshiriq": "Kiberxavfsizlik talablari bo'yicha xodimlar attestatsiyasini o'tkazish",
            "Masul": "Axmedov Bobur",
            "Berilgan_sana": d_str(-10),
            "Muddat": d_str(5),   # <= 7 days, foiz < 60 -> O'rta risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 40.0,
            "Ustuvorlik": "Orta",
            "Izoh": "3 ta filial qamrab olindi"
        },
        {
            "ID": "AKT-204",
            "Boshqarma": "AKT boshqarmasi",
            "Topshiriq": "Elektron hujjat aylanishi (EDO) yangi versiyasiga o'tish",
            "Masul": "Qodirov Anvar",
            "Berilgan_sana": d_str(-25),
            "Muddat": d_str(-2),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Tizim barqaror ishlamoqda"
        },

        # Kadrlar boshqarmasi
        {
            "ID": "KB-301",
            "Boshqarma": "Kadrlar boshqarmasi",
            "Topshiriq": "Yangi qabul qilingan mutaxassislar malakasini oshirish rejasini tasdiqlash",
            "Masul": "Sultonova Dildora",
            "Berilgan_sana": d_str(-8),
            "Muddat": d_str(2),   # <= 3 days, foiz >= 80 -> Past
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 85.0,
            "Ustuvorlik": "Orta",
            "Izoh": "Buyruq loyihasi tayyor"
        },
        {
            "ID": "KB-302",
            "Boshqarma": "Kadrlar boshqarmasi",
            "Topshiriq": "Mehnat xavfsizligi bo'yicha yillik majburiy tibbiy ko'rik o'tkazish",
            "Masul": "Yuldashev Akmal",
            "Berilgan_sana": d_str(-35),
            "Muddat": d_str(-4),  # Overdue -> Kritik
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 65.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Klinika bilan shartnoma yakunlanmoqda"
        },
        {
            "ID": "KB-303",
            "Boshqarma": "Kadrlar boshqarmasi",
            "Topshiriq": "2026-yil xodimlar shtat jadvaliga kiritilgan o'zgarishlarni hisobga olish",
            "Masul": "Sultonova Dildora",
            "Berilgan_sana": d_str(-18),
            "Muddat": d_str(-1),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Orta",
            "Izoh": "Adliya organlari bilan kelishildi"
        },
        {
            "ID": "KB-304",
            "Boshqarma": "Kadrlar boshqarmasi",
            "Topshiriq": "Yosh mutaxassislar uchun mentorlik dasturini joriy etish",
            "Masul": "Yuldashev Akmal",
            "Berilgan_sana": d_str(-4),
            "Muddat": d_str(18),
            "Holat": "Boshlanmagan",
            "Bajarilish_foizi": 0.0,
            "Ustuvorlik": "Past",
            "Izoh": "Taqsimot rejalashtirilmoqda"
        },

        # Yuridik boshqarma
        {
            "ID": "YB-401",
            "Boshqarma": "Yuridik boshqarma",
            "Topshiriq": "Xalqaro pudratchilar bilan tuzilgan shartnomalarni huquqiy ekspertizadan o'tkazish",
            "Masul": "Normatov Sherzod",
            "Berilgan_sana": d_str(-12),
            "Muddat": d_str(3),   # <= 3 days, foiz < 80 -> Yuqori risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 50.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "E'tirozlar ko'rib chiqilmoqda"
        },
        {
            "ID": "YB-402",
            "Boshqarma": "Yuridik boshqarma",
            "Topshiriq": "Debitor qarzdorliklarni undirish bo'yicha iqtisodiy sudga da'vo arizalari kiritish",
            "Masul": "Normatov Sherzod",
            "Berilgan_sana": d_str(-25),
            "Muddat": d_str(-7),  # Overdue -> Kritik
            "Holat": "Kechikkan",
            "Bajarilish_foizi": 30.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Qo'shimcha dalillar to'planmoqda"
        },
        {
            "ID": "YB-403",
            "Boshqarma": "Yuridik boshqarma",
            "Topshiriq": "Ichki normativ-huquqiy hujjatlarni yangilangan qonunchilikka muvofiqlashtirish",
            "Masul": "Ergashev Mansur",
            "Berilgan_sana": d_str(-15),
            "Muddat": d_str(12),
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 80.0,
            "Ustuvorlik": "Orta",
            "Izoh": "10 ta buyruq ko'rib chiqildi"
        },
        {
            "ID": "YB-404",
            "Boshqarma": "Yuridik boshqarma",
            "Topshiriq": "Xodimlar bilan tuziladigan namunaviy mehnat shartnomasini qayta tasdiqlash",
            "Masul": "Ergashev Mansur",
            "Berilgan_sana": d_str(-10),
            "Muddat": d_str(-2),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Past",
            "Izoh": "Yakunlandi"
        },

        # Ijro nazorati boshqarmasi
        {
            "ID": "IN-501",
            "Boshqarma": "Ijro nazorati boshqarmasi",
            "Topshiriq": "Prezident qarorlari va farmoyishlari ijrosi bo'yicha oylik hisobotni tayyorlash",
            "Masul": "G'aniyev Alisher",
            "Berilgan_sana": d_str(-20),
            "Muddat": d_str(1),   # <= 3 days, foiz 75% -> Yuqori risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 75.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Filiallar ma'lumotlari jamlandi"
        },
        {
            "ID": "IN-502",
            "Boshqarma": "Ijro nazorati boshqarmasi",
            "Topshiriq": "Vazirlar Mahkamasi topshiriqlarining ijro intizomi monitoringi rejasini bajarish",
            "Masul": "G'aniyev Alisher",
            "Berilgan_sana": d_str(-15),
            "Muddat": d_str(6),   # <= 7 days, foiz 40% -> O'rta risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 40.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Nazorat kartochkalari ochildi"
        },
        {
            "ID": "IN-503",
            "Boshqarma": "Ijro nazorati boshqarmasi",
            "Topshiriq": "Murojaatlar bilan ishlash bo'yicha 'Qabulxona' faoliyatini kompleks tekshirish",
            "Masul": "Mirzayev Farhod",
            "Berilgan_sana": d_str(-30),
            "Muddat": d_str(-3),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Orta",
            "Izoh": "Kamchiliklar bartaraf etildi"
        },
        {
            "ID": "IN-504",
            "Boshqarma": "Ijro nazorati boshqarmasi",
            "Topshiriq": "Ijro intizomini buzgan mansabdor shaxslarga nisbatan chora ko'rish to'g'risida taqdimnoma",
            "Masul": "Mirzayev Farhod",
            "Berilgan_sana": d_str(-28),
            "Muddat": d_str(-6),  # Overdue -> Kritik
            "Holat": "Kechikkan",
            "Bajarilish_foizi": 20.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Rahbariyat ko'rib chiqmoqda"
        },

        # Strategik rivojlanish boshqarmasi
        {
            "ID": "SR-601",
            "Boshqarma": "Strategik rivojlanish boshqarmasi",
            "Topshiriq": "Qayta tiklanuvchi energiya manbalarini joriy etish konsepsiyasini ishlab chiqish",
            "Masul": "Sobirov Umid",
            "Berilgan_sana": d_str(-45),
            "Muddat": d_str(4),   # <= 7 days, foiz 55% -> O'rta risk
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 55.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Ekspertlar guruhi baholamoqda"
        },
        {
            "ID": "SR-602",
            "Boshqarma": "Strategik rivojlanish boshqarmasi",
            "Topshiriq": "Elektr stansiyalari energiya samaradorligini oshirish bo'yicha 5 yillik yo'l xaritasi",
            "Masul": "Sobirov Umid",
            "Berilgan_sana": d_str(-50),
            "Muddat": d_str(-12), # Overdue -> Kritik
            "Holat": "Kechikkan",
            "Bajarilish_foizi": 60.0,
            "Ustuvorlik": "Yuqori",
            "Izoh": "Vazirlik bilan kelishuv kutilmoqda"
        },
        {
            "ID": "SR-603",
            "Boshqarma": "Strategik rivojlanish boshqarmasi",
            "Topshiriq": "Yaponiyalik hamkorlar bilan texnologik tajriba almashish seminari",
            "Masul": "Hamidova Gulnoza",
            "Berilgan_sana": d_str(-20),
            "Muddat": d_str(-5),
            "Holat": "Bajarildi",
            "Bajarilish_foizi": 100.0,
            "Ustuvorlik": "Orta",
            "Izoh": "Muvaffaqiyatli o'tkazildi"
        },
        {
            "ID": "SR-604",
            "Boshqarma": "Strategik rivojlanish boshqarmasi",
            "Topshiriq": "Raqamli transformatsiya va sun'iy intellekt modullarini sinovdan o'tkazish",
            "Masul": "Hamidova Gulnoza",
            "Berilgan_sana": d_str(-10),
            "Muddat": d_str(20),
            "Holat": "Jarayonda",
            "Bajarilish_foizi": 35.0,
            "Ustuvorlik": "Orta",
            "Izoh": "Tajriba maydonchasi tanlandi"
        },
        {
            "ID": "SR-605",
            "Boshqarma": "Strategik rivojlanish boshqarmasi",
            "Topshiriq": "2030-yilgacha bo'lgan rivojlanish strategiyasi taqdimoti",
            "Masul": "Sobirov Umid",
            "Berilgan_sana": d_str(-5),
            "Muddat": d_str(30),
            "Holat": "Boshlanmagan",
            "Bajarilish_foizi": 0.0,
            "Ustuvorlik": "Past",
            "Izoh": "Boshlang'ich bosqichda"
        }
    ]

    df = pd.DataFrame(sample_tasks)
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")
    logger.info("Sample Excel created at: %s with %d tasks", EXCEL_PATH, len(sample_tasks))

def read_and_sync_excel(db: Session, excel_path: str = EXCEL_PATH) -> dict:
    """
    Safely reads ijro.xlsx, recalculates risk, syncs SQLite, and logs results.
    """
    create_sample_excel_if_missing()

    if not os.path.exists(excel_path):
        err_msg = f"Excel fayli topilmadi: {excel_path}"
        logger.error(err_msg)
        return {"success": False, "message": err_msg, "total": 0, "synced": 0, "errors": 1}

    # Wait briefly if Excel is being written (retry mechanism for locks)
    df = None
    max_retries = 8
    for attempt in range(max_retries):
        try:
            if os.path.exists(excel_path) and os.path.getsize(excel_path) > 0:
                df = pd.read_excel(excel_path, engine="openpyxl")
                if df is not None and len(df) > 0:
                    break
        except Exception as e:
            logger.warning("Attempt %d/%d: Excel file is busy or locked: %s", attempt + 1, max_retries, e)
        time.sleep(0.4)

    if df is None:
        err_msg = "Excel faylini o'qib bo'lmadi (fayl boshqa dasturda ochiq bo'lishi mumkin)."
        logger.error(err_msg)
        log = ImportLog(
            import_time=datetime.now(),
            total_rows=0,
            successful_rows=0,
            error_rows=1,
            file_name=os.path.basename(excel_path),
            status="ERROR",
            message=err_msg
        )
        db.add(log)
        db.commit()
        return {"success": False, "message": err_msg, "total": 0, "synced": 0, "errors": 1, "last_updated": log.import_time.strftime("%d.%m.%Y %H:%M:%S")}

    # Normalize column names (strip whitespace and case match)
    col_mapping = {}
    for col in df.columns:
        cleaned = str(col).strip()
        for req in REQUIRED_COLUMNS:
            if cleaned.lower() == req.lower():
                col_mapping[col] = req
                break
    df.rename(columns=col_mapping, inplace=True)

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        err_msg = f"Excelda majburiy ustunlar yetishmaydi: {', '.join(missing_cols)}"
        logger.error(err_msg)
        log = ImportLog(
            import_time=datetime.utcnow(),
            total_rows=len(df),
            successful_rows=0,
            error_rows=len(df),
            file_name=os.path.basename(excel_path),
            status="ERROR",
            message=err_msg
        )
        db.add(log)
        db.commit()
        return {"success": False, "message": err_msg, "total": len(df), "synced": 0, "errors": len(df)}

    total_rows = len(df)
    successful_rows = 0
    error_rows = 0

    seen_ids = set()

    # Clear old tasks or update in place
    existing_tasks = {t.id: t for t in db.query(Task).all()}
    active_ids = []

    for idx, row in df.iterrows():
        try:
            raw_id = str(row.get("ID", "")).strip()
            if not raw_id or raw_id == "nan":
                raw_id = f"TASK-{idx + 1}"

            if raw_id in seen_ids:
                raw_id = f"{raw_id}-{idx + 1}"
            seen_ids.add(raw_id)
            active_ids.append(raw_id)

            boshqarma = str(row.get("Boshqarma", "Noma'lum")).strip()
            topshiriq = str(row.get("Topshiriq", "Nomsiz topshiriq")).strip()
            masul = str(row.get("Masul", "Noma'lum")).strip()

            # Dates
            berilgan = parse_date(row.get("Berilgan_sana"))
            berilgan_sana = berilgan.strftime("%Y-%m-%d") if berilgan else ""

            muddat_date = parse_date(row.get("Muddat"))
            muddat = muddat_date.strftime("%Y-%m-%d") if muddat_date else ""

            # Percentage
            try:
                raw_foiz = row.get("Bajarilish_foizi", 0.0)
                if pd.isna(raw_foiz):
                    foiz = 0.0
                else:
                    foiz = float(raw_foiz)
                    if foiz > 0 and foiz <= 1.0 and ("%" not in str(raw_foiz)):
                        # If decimal proportion like 0.75
                        foiz = foiz * 100.0
                    foiz = max(0.0, min(100.0, foiz))
            except Exception:
                foiz = 0.0

            # Status normalization
            holat = str(row.get("Holat", "Boshlanmagan")).strip().capitalize()
            if holat not in ["Bajarildi", "Jarayonda", "Boshlanmagan", "Kechikkan"]:
                if foiz >= 100.0:
                    holat = "Bajarildi"
                elif foiz > 0:
                    holat = "Jarayonda"
                else:
                    holat = "Boshlanmagan"

            ustuvorlik = str(row.get("Ustuvorlik", "Orta")).strip().capitalize()
            if ustuvorlik not in ["Yuqori", "Orta", "Past"]:
                ustuvorlik = "Orta"

            izoh = "" if pd.isna(row.get("Izoh")) else str(row.get("Izoh")).strip()

            # Calculate risk
            days_rem, risk_level, is_overdue = calculate_task_risk(
                muddat_date, holat, foiz
            )

            if raw_id in existing_tasks:
                task = existing_tasks[raw_id]
                task.boshqarma = boshqarma
                task.topshiriq = topshiriq
                task.masul = masul
                task.berilgan_sana = berilgan_sana
                task.muddat = muddat
                task.holat = holat
                task.bajarilish_foizi = foiz
                task.ustuvorlik = ustuvorlik
                task.izoh = izoh
                task.days_remaining = days_rem
                task.risk_level = risk_level
                task.is_overdue = is_overdue
                task.updated_at = datetime.utcnow()
            else:
                task = Task(
                    id=raw_id,
                    boshqarma=boshqarma,
                    topshiriq=topshiriq,
                    masul=masul,
                    berilgan_sana=berilgan_sana,
                    muddat=muddat,
                    holat=holat,
                    bajarilish_foizi=foiz,
                    ustuvorlik=ustuvorlik,
                    izoh=izoh,
                    days_remaining=days_rem,
                    risk_level=risk_level,
                    is_overdue=is_overdue,
                    updated_at=datetime.utcnow()
                )
                db.add(task)
            successful_rows += 1
        except Exception as err:
            logger.error("Error processing row %d: %s", idx, err)
            error_rows += 1

    # Remove tasks no longer in Excel
    for t_id, t_obj in existing_tasks.items():
        if t_id not in active_ids:
            db.delete(t_obj)

    # Log import
    now = datetime.now()
    log = ImportLog(
        import_time=now,
        total_rows=total_rows,
        successful_rows=successful_rows,
        error_rows=error_rows,
        file_name=os.path.basename(excel_path),
        status="SUCCESS" if error_rows == 0 else "PARTIAL",
        message=f"{successful_rows} ta topshiriq muvaffaqiyatli sinxronlandi."
    )
    db.add(log)
    db.commit()

    last_updated_str = now.strftime("%d.%m.%Y %H:%M:%S")
    logger.info("Excel sync complete: %d total, %d synced, %d errors. Last updated: %s", total_rows, successful_rows, error_rows, last_updated_str)
    return {
        "success": True,
        "message": f"{successful_rows} ta topshiriq sinxronlandi",
        "total": total_rows,
        "synced": successful_rows,
        "errors": error_rows,
        "last_updated": last_updated_str
    }
