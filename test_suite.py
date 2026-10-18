import os
import io
from datetime import datetime, date, timedelta
import pandas as pd
from backend.database import SessionLocal
from backend.models import Task
from backend.universal_excel_parser import (
    process_multiple_excel_files, refresh_all_local_excels,
    save_column_mapping, parse_single_excel, sync_records_to_database,
    UPLOADS_DIR
)

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_excels")
os.makedirs(TEST_DIR, exist_ok=True)

today = date.today()
past_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
near_future_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
med_future_date = (today + timedelta(days=6)).strftime("%Y-%m-%d")
far_future_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")

def generate_8_test_files():
    files = {}

    # 1. Uzbek Standard (header row 0, Sheet: 'Ijro')
    df1 = pd.DataFrame([
        {"ID": "UZ-1", "Boshqarma": "Moliya boshqarmasi", "Topshiriq": "2026 yil byudjetini tasdiqlash", "Mas'ul": "Olimov R.", "Muddat": far_future_date, "Holat": "Jarayonda", "Bajarilish (%)": 65, "Ustuvorlik": "Yuqori"},
        {"ID": "UZ-2", "Boshqarma": "Moliya boshqarmasi", "Topshiriq": "Moliyaviy hisobotni topshirish", "Mas'ul": "Karimov S.", "Muddat": near_future_date, "Holat": "Jarayonda", "Bajarilish (%)": 30, "Ustuvorlik": "Orta"},
        {"ID": "UZ-3", "Boshqarma": "Moliya boshqarmasi", "Topshiriq": "Audit xulosasini tayyorlash", "Mas'ul": "Olimov R.", "Muddat": far_future_date, "Holat": "Bajarildi", "Bajarilish (%)": 100, "Ustuvorlik": "Past"},
    ])
    p1 = os.path.join(TEST_DIR, "file1_uzbek_standard.xlsx")
    with pd.ExcelWriter(p1, engine="openpyxl") as w:
        df1.to_excel(w, index=False, sheet_name="Ijro")
    files["file1_uzbek_standard.xlsx"] = p1

    # 2. Russian Headers (header row 2, title on top, Sheet: 'Реестр_поручений', summary row 'Итого')
    p2 = os.path.join(TEST_DIR, "file2_russian_headers.xlsx")
    wb_data = [
        ["ОТЧЕТ ПО КОНТРОЛЮ ИСПОЛНЕНИЯ ПОРУЧЕНИЙ", "", "", "", "", "", "", ""],
        ["Дата формирования: 2026-10-14", "", "", "", "", "", "", ""],
        ["№ п/п", "Управление", "Поручение", "Ответственный", "Срок исполнения", "Статус", "Процент выполнения", "Приоритет"],
        ["RU-1", "AKT boshqarmasi", "ERP tizimini modernizatsiya qilish", "Axmedov B.", far_future_date, "В процессе", "75%", "Высокий"],
        ["RU-2", "AKT boshqarmasi", "Server uskunalarini xarid qilish", "Toshmatov D.", past_date, "В процессе", "50%", "Высокий"],
        ["RU-3", "AKT boshqarmasi", "Kiberxavfsizlik auditini yakunlash", "Axmedov B.", far_future_date, "Выполнено", "100%", "Средний"],
        ["Итого", "Всего поручений: 3", "", "", "", "", "75%", ""],
    ]
    df2 = pd.DataFrame(wb_data)
    with pd.ExcelWriter(p2, engine="openpyxl") as w:
        df2.to_excel(w, index=False, header=False, sheet_name="Реестр_поручений")
    files["file2_russian_headers.xlsx"] = p2

    # 3. English Headers (different order, Sheet: 'Monitoring_2026', summary row 'Total')
    df3 = pd.DataFrame([
        {"Progress": "85%", "Assignee": "Sultonova D.", "Department": "Kadrlar boshqarmasi", "Task Description": "Kadrlar zaxirasini shakllantirish", "Deadline": far_future_date, "Task ID": "EN-1", "Status": "In Progress", "Urgency": "High"},
        {"Progress": "100%", "Assignee": "Aliyev N.", "Department": "Kadrlar boshqarmasi", "Task Description": "Malaka oshirish kurslarini tashkil etish", "Deadline": past_date, "Task ID": "EN-2", "Status": "Completed", "Urgency": "Medium"},
        {"Progress": "0%", "Assignee": "Sultonova D.", "Department": "Kadrlar boshqarmasi", "Task Description": "Yangi xodimlarni attestatsiyadan o'tkazish", "Deadline": med_future_date, "Task ID": "EN-3", "Status": "Not Started", "Urgency": "Low"},
        {"Progress": "61%", "Assignee": "Total", "Department": "Total", "Task Description": "Total", "Deadline": "", "Task ID": "Total", "Status": "", "Urgency": ""},
    ])
    p3 = os.path.join(TEST_DIR, "file3_english_headers.xlsx")
    with pd.ExcelWriter(p3, engine="openpyxl") as w:
        df3.to_excel(w, index=False, sheet_name="Monitoring_2026")
    files["file3_english_headers.xlsx"] = p3

    # 4. Cyrillic Uzbek (header row 1, Sheet: 'Назорат')
    p4 = os.path.join(TEST_DIR, "file4_cyrillic_uzbek.xlsx")
    wb_data4 = [
        ["ИЖРО ИНТИЗОМИ НАЗОРАТИ ВА ТАҲЛИЛИ", "", "", "", "", "", "", ""],
        ["Т/р", "Бошқарма", "Топшириқ", "Ижрочи", "Муддат", "Ҳолат", "Бажарилиши", "Даража"],
        ["CY-1", "Yuridik boshqarma", "Shartnomalar ekspertizasini o'tkazish", "Normatov Sh.", far_future_date, "Жараёнда", 90, "Юқори"],
        ["CY-2", "Yuridik boshqarma", "Yangi nizom loyihasini ishlab chiqish", "Yusupov M.", past_date, "Жараёнда", 40, "Юқори"],
    ]
    df4 = pd.DataFrame(wb_data4)
    with pd.ExcelWriter(p4, engine="openpyxl") as w:
        df4.to_excel(w, index=False, header=False, sheet_name="Назорат")
    files["file4_cyrillic_uzbek.xlsx"] = p4

    # 5. Shuffled Columns with Header on row 3 (Sheet: 'Sheet1', summary row 'Jami:')
    p5 = os.path.join(TEST_DIR, "file5_shuffled_different_order.xlsx")
    wb_data5 = [
        ["", "", "", "", "", ""],
        ["KOMPANIYA IJRO MONITORINGI", "", "", "", "", ""],
        ["2026-yil 3-chorak", "", "", "", "", ""],
        ["Bajarilish foizi", "Oxirgi muddat", "Topshiriq mazmuni", "Boshqarma nomi", "Mas'ul shaxs", "Kod"],
        ["50%", far_future_date, "Strategik reja ishlab chiqish", "Strategik rivojlanish boshqarmasi", "Sobirov U.", "ST-1"],
        ["100%", past_date, "Tashqi bozorlar tahlili", "Strategik rivojlanish boshqarmasi", "Sobirov U.", "ST-2"],
        ["15%", near_future_date, "Investitsiya dasturini yangilash", "Strategik rivojlanish boshqarmasi", "Ergashev A.", "ST-3"],
        ["Jami:", "", "", "", "", ""],
    ]
    df5 = pd.DataFrame(wb_data5)
    with pd.ExcelWriter(p5, engine="openpyxl") as w:
        df5.to_excel(w, index=False, header=False, sheet_name="Sheet1")
    files["file5_shuffled_different_order.xlsx"] = p5

    # 6. Overdue Tasks (deadline in past and not 100% -> must be is_overdue=True, risk=Kritik)
    df6 = pd.DataFrame([
        {"ID": "OVD-1", "Boshqarma": "Ijro nazorati boshqarmasi", "Topshiriq": "Prezident qarori ijrosi hisoboti", "Mas'ul": "G'aniyev A.", "Muddat": past_date, "Holat": "Kechikkan", "Bajarilish_foizi": 45, "Ustuvorlik": "Yuqori"},
        {"ID": "OVD-2", "Boshqarma": "Ijro nazorati boshqarmasi", "Topshiriq": "Ijro intizomi reyd tekshiruvi", "Mas'ul": "G'aniyev A.", "Muddat": past_date, "Holat": "Jarayonda", "Bajarilish_foizi": 20, "Ustuvorlik": "Yuqori"},
    ])
    p6 = os.path.join(TEST_DIR, "file6_overdue_tasks.xlsx")
    with pd.ExcelWriter(p6, engine="openpyxl") as w:
        df6.to_excel(w, index=False, sheet_name="Ijro")
    files["file6_overdue_tasks.xlsx"] = p6

    # 7. Completed and High Risk (test risk rules: days <= 3 & foiz < 80 => Yuqori, days <= 7 & foiz < 60 => O'rta)
    df7 = pd.DataFrame([
        {"ID": "RSK-1", "Boshqarma": "Moliya boshqarmasi", "Topshiriq": "Soliq hisobotini topshirish", "Mas'ul": "Olimov R.", "Muddat": near_future_date, "Holat": "Jarayonda", "Bajarilish (%)": 25, "Ustuvorlik": "Yuqori"},
        {"ID": "RSK-2", "Boshqarma": "Kadrlar boshqarmasi", "Topshiriq": "Tabel hisobotini shakllantirish", "Mas'ul": "Sultonova D.", "Muddat": med_future_date, "Holat": "Jarayonda", "Bajarilish (%)": 40, "Ustuvorlik": "Orta"},
        {"ID": "RSK-3", "Boshqarma": "Yuridik boshqarma", "Topshiriq": "Yillik hisobotni rasmiylashtirish", "Mas'ul": "Normatov Sh.", "Muddat": far_future_date, "Holat": "Bajarildi", "Bajarilish (%)": 100, "Ustuvorlik": "Past"},
    ])
    p7 = os.path.join(TEST_DIR, "file7_completed_and_high_risk.xlsx")
    with pd.ExcelWriter(p7, engine="openpyxl") as w:
        df7.to_excel(w, index=False, sheet_name="Risk_Guruhlari")
    files["file7_completed_and_high_risk.xlsx"] = p7

    # 8. Unrecognized Columns (for testing manual column mapping dialog Requirement 14)
    df8 = pd.DataFrame([
        {"Tashkiliy_Birlik": "AKT boshqarmasi", "Vazifaning_Toliq_Matni": "Yangi server xonasi sovutish tizimini o'rnatish", "Bajaruvchi_Xodim": "Axmedov B.", "Bajarish_Kuni": far_future_date, "Holat_Kodi": "Jarayonda", "Foiz_Darajasi": 55, "Muhimlik": "Yuqori"},
        {"Tashkiliy_Birlik": "AKT boshqarmasi", "Vazifaning_Toliq_Matni": "Optik tolali kabel yotqizish", "Bajaruvchi_Xodim": "Toshmatov D.", "Bajarish_Kuni": near_future_date, "Holat_Kodi": "Jarayonda", "Foiz_Darajasi": 10, "Muhimlik": "Yuqori"},
    ])
    p8 = os.path.join(TEST_DIR, "file8_custom_columns_for_mapping.xlsx")
    with pd.ExcelWriter(p8, engine="openpyxl") as w:
        df8.to_excel(w, index=False, sheet_name="DataSheet")
    files["file8_custom_columns_for_mapping.xlsx"] = p8

    return files

def run_tests():
    print("=== Generating 8 varied Excel files ===")
    files = generate_8_test_files()
    print(f"Generated {len(files)} files in {TEST_DIR}")

    db = SessionLocal()
    try:
        # TEST 1: Multi-file import of files 1 to 7 simultaneously (Requirement 1)
        print("\n--- TEST 1: Simultaneous Multi-File Import (Files 1 to 7) ---")
        files_data = []
        for name in list(files.keys())[:7]:
            with open(files[name], "rb") as f:
                files_data.append((name, f.read()))

        res1 = process_multiple_excel_files(db, files_data)
        print(f"Import result: success={res1['success']}, processed={len(res1['processed_files'])}, failed={len(res1['failed_files'])}")
        assert len(res1['processed_files']) == 7, f"Expected 7 processed files, got {len(res1['processed_files'])}"

        # TEST 2: Verify Summary Row Filtering (Requirement 8)
        print("\n--- TEST 2: Summary Row Exclusion (Jami / Итого / Total) ---")
        tasks = db.query(Task).all()
        summary_tasks = [t for t in tasks if t.topshiriq.strip().lower() in ["jami", "итого", "всего", "total"]]
        print(f"Total active tasks: {len(tasks)}, Summary rows found: {len(summary_tasks)}")
        assert len(summary_tasks) == 0, "Summary rows were not excluded!"

        # TEST 3: Verify Overdue Calculation (Requirement 6)
        print("\n--- TEST 3: Overdue Calculation (deadline < today AND not completed) ---")
        overdue_tasks = [t for t in tasks if t.is_overdue]
        print(f"Overdue tasks count: {len(overdue_tasks)}")
        for t in overdue_tasks:
            assert t.bajarilish_foizi < 100.0 and t.holat != "Bajarildi", f"Completed task marked overdue: {t.id}"
            assert t.risk_level == "Kritik", f"Overdue task should have Kritik risk: {t.id}"

        # TEST 4: Prevent Duplicates on Re-import (Requirement 9)
        print("\n--- TEST 4: Duplicate Prevention on Re-import ---")
        count_before = db.query(Task).count()
        file1_bytes = files_data[0][1]
        res_reimport = process_multiple_excel_files(db, [("file1_uzbek_standard.xlsx", file1_bytes)])
        count_after = db.query(Task).count()
        print(f"Count before re-import: {count_before}, Count after re-import: {count_after}")
        assert count_before == count_after, f"Duplicate detected! Before: {count_before}, After: {count_after}"

        # TEST 5: Source File Tracking (Requirement 10)
        print("\n--- TEST 5: Source File Stored For Each Record ---")
        distinct_sources = [s[0] for s in db.query(Task.source_file).distinct().all()]
        print(f"Distinct source files in DB: {distinct_sources}")
        assert len(distinct_sources) >= 7, f"Expected at least 7 source files, got {len(distinct_sources)}"

        # TEST 6: Unknown Structure Mapping (Requirement 14)
        print("\n--- TEST 6: Unknown Structure Detection & Manual Column Mapping ---")
        with open(files["file8_custom_columns_for_mapping.xlsx"], "rb") as f:
            f8_bytes = f.read()
        res8 = parse_single_excel(io.BytesIO(f8_bytes), "file8_custom_columns_for_mapping.xlsx")
        print(f"File 8 without mapping needs_mapping: {res8.get('needs_mapping')}")
        assert res8.get("needs_mapping") == True, "File 8 with unknown columns should require mapping!"

        # Now save mapping for File 8
        mapping8 = {
            "Tashkiliy_Birlik": "Boshqarma",
            "Vazifaning_Toliq_Matni": "Topshiriq",
            "Bajaruvchi_Xodim": "Masul",
            "Bajarish_Kuni": "Muddat",
            "Holat_Kodi": "Holat",
            "Foiz_Darajasi": "Bajarilish_foizi",
            "Muhimlik": "Ustuvorlik"
        }
        save_column_mapping("file8_custom_columns_for_mapping.xlsx", mapping8)
        res8_mapped = parse_single_excel(io.BytesIO(f8_bytes), "file8_custom_columns_for_mapping.xlsx", custom_mapping=mapping8)
        print(f"File 8 with mapping: success={res8_mapped['success']}, parsed={res8_mapped.get('total_parsed')}")
        assert res8_mapped["success"] == True and res8_mapped["total_parsed"] == 2, "File 8 failed after column mapping!"

        # Sync file 8 to database
        sync_records_to_database(db, "file8_custom_columns_for_mapping.xlsx", res8_mapped["records"])

        # TEST 7: Resilient Import with 1 Failed File (Requirement 15)
        print("\n--- TEST 7: Resilient Import (Valid files updated, failed file preserves prior data) ---")
        prior_file8_count = db.query(Task).filter(Task.source_file == "file8_custom_columns_for_mapping.xlsx").count()
        # Upload a corrupted / invalid version of file 8 along with valid file 1
        corrupt_bytes = b"Corrupted invalid excel content"
        res_resilient = process_multiple_excel_files(db, [
            ("file1_uzbek_standard.xlsx", file1_bytes),
            ("file8_custom_columns_for_mapping.xlsx", corrupt_bytes)
        ])
        print(f"Resilient test processed={len(res_resilient['processed_files'])}, failed={len(res_resilient['failed_files'])}")
        post_file8_count = db.query(Task).filter(Task.source_file == "file8_custom_columns_for_mapping.xlsx").count()
        print(f"File 8 records before: {prior_file8_count}, after failed upload: {post_file8_count}")
        assert post_file8_count == prior_file8_count, "Prior valid records were lost on failed upload!"

        # TEST 8: Refresh All Local Excels (Requirement 13)
        print("\n--- TEST 8: Refresh All Local Excels ---")
        refresh_res = refresh_all_local_excels(db)
        print(f"Refresh all result: success={refresh_res['success']}, total records={db.query(Task).count()}")
        assert refresh_res["success"] == True

        print("\n=======================================================")
        print("ALL 8 EXCEL FILE TESTS PASSED WITH 100% SUCCESS!")
        print("=======================================================")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
