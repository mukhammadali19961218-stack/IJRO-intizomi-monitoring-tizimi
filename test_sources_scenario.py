import os
import io
import shutil
from datetime import datetime, date, timedelta
import pandas as pd

from backend.database import SessionLocal, check_and_apply_migrations
from backend.models import Task
from backend.task_sources_manager import (
    DEFAULT_TASK_SOURCES,
    get_all_task_sources_info,
    upload_and_replace_task_excel,
    delete_task_source,
    refresh_single_task_source,
    refresh_all_task_sources,
    calculate_single_task_summary,
    get_task_current_excel_path,
    TASKS_DIR
)
from backend.main import get_summary

today = date.today()
past_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
near_future_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
med_future_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
far_future_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")

def generate_sample_excel(count: int, prefix: str) -> bytes:
    """Generates an in-memory Excel file with the given number of tasks."""
    rows = []
    departments = [
        "Moliya boshqarmasi",
        "AKT boshqarmasi",
        "Kadrlar boshqarmasi",
        "Yuridik boshqarma",
        "Ijro nazorati boshqarmasi",
        "Strategik rivojlanish boshqarmasi"
    ]
    for i in range(1, count + 1):
        dept = departments[(i - 1) % len(departments)]
        # Varied statuses & deadlines
        if i % 4 == 0:
            status = "Bajarildi"
            foiz = 100.0
            muddat = far_future_date
            priority = "Past"
        elif i % 4 == 1:
            status = "Jarayonda"
            foiz = 60.0
            muddat = near_future_date
            priority = "Yuqori"
        elif i % 4 == 2:
            status = "Kechikkan"
            foiz = 30.0
            muddat = past_date
            priority = "Yuqori"
        else:
            status = "Boshlanmagan"
            foiz = 0.0
            muddat = med_future_date
            priority = "Orta"

        rows.append({
            "ID": f"{prefix}-{i}",
            "Boshqarma": dept,
            "Topshiriq": f"{prefix} doirasidagi topshiriq #{i} mazmuni",
            "Mas'ul": f"Xodim_{prefix}_{i}",
            "Muddat": muddat,
            "Holat": status,
            "Bajarilish (%)": foiz,
            "Ustuvorlik": priority
        })

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Topshiriqlar")
    buf.seek(0)
    return buf.read()

def run_scenario():
    check_and_apply_migrations()
    db = SessionLocal()

    try:
        print("\n==================================================================")
        print("STARTING TEST SCENARIO (REQUIREMENTS 1 to 16)")
        print("==================================================================")

        # Clean previous test tasks
        db.query(Task).delete()
        db.commit()

        # Step 1: Import Excel for 8 separate tasks
        print("\n--- STEP 1: Importing Excel for 8 Separate Tasks ---")
        task_counts = {
            "task_1": 10,
            "task_2": 15,
            "task_3": 20,
            "task_4": 120,  # Requirement 3 user example (old = 120)
            "task_5": 12,
            "task_6": 8,
            "task_7": 14,
            "task_8": 11,
        }

        task_files = {}
        for sid, count in task_counts.items():
            fname = f"{sid}_initial.xlsx"
            fbytes = generate_sample_excel(count, sid.upper())
            task_files[sid] = (fname, fbytes)
            
            res = upload_and_replace_task_excel(db, sid, fname, fbytes)
            assert res["success"] == True, f"Upload failed for {sid}: {res.get('error')}"
            assert res["synced_count"] == count, f"Expected {count} for {sid}, got {res['synced_count']}"
            print(f"[PASS] {sid} ({fname}): {res['synced_count']} records imported")

        # Step 2: Confirm each task has its own summary and current.xlsx exists
        print("\n--- STEP 2: Confirm Each Task Has Its Own Summary & current.xlsx ---")
        sources_info = get_all_task_sources_info(db)
        assert len(sources_info) == 8, f"Expected 8 task sources, got {len(sources_info)}"

        for s in sources_info:
            sid = s["source_id"]
            expected_count = task_counts[sid]
            assert s["has_file"] == True, f"{sid} should have has_file=True"
            assert s["total_records"] == expected_count, f"{sid} DB count mismatch"
            
            current_path = get_task_current_excel_path(sid)
            assert os.path.exists(current_path), f"{current_path} does not exist"
            
            sumry = s["summary"]
            assert sumry is not None
            assert sumry["jami_topshiriqlar"] == expected_count
            print(f"[PASS] {sid} Summary: Jami={sumry['jami_topshiriqlar']}, Bajarilgan={sumry['bajarilgan']}, Jarayonda={sumry['jarayonda']}, Kechikkan={sumry['muddati_otgan']}, Foiz={sumry['umumiy_bajarilish_foizi']}%")

        # Step 3: Confirm Umumiy Svod combines all 8 current sources
        print("\n--- STEP 3: Confirm Combined 'Umumiy Svod' ---")
        expected_total_svod = sum(task_counts.values())  # 10+15+20+120+12+8+14+11 = 210
        total_in_db = db.query(Task).count()
        print(f"Expected combined total: {expected_total_svod}, Total tasks in DB: {total_in_db}")
        assert total_in_db == expected_total_svod, f"Expected {expected_total_svod}, got {total_in_db}"

        svod_summary = get_summary(db=db)
        assert svod_summary.jami_topshiriqlar == expected_total_svod
        print(f"[PASS] Umumiy Svod: Jami={svod_summary.jami_topshiriqlar}, Bajarilgan={svod_summary.bajarilgan}, Jarayonda={svod_summary.jarayonda}, Kechikkan={svod_summary.muddati_otgan}, Foiz={svod_summary.umumiy_bajarilish_foizi}%")

        # Step 4: Replace ONLY Topshiriq 4 Excel (120 records -> 85 records)
        print("\n--- STEP 4: Replace ONLY Topshiriq 4 Excel (Old: 120 records -> New: 85 records) ---")
        new_task4_count = 85  # User example: Topshiriq new Excel = 85 records
        new_task4_bytes = generate_sample_excel(new_task4_count, "TASK_4_NEW")
        
        res_replace = upload_and_replace_task_excel(db, "task_4", "task_4_updated.xlsx", new_task4_bytes)
        assert res_replace["success"] == True
        assert res_replace["synced_count"] == 85
        print(f"[PASS] Topshiriq 4 successfully replaced with {res_replace['synced_count']} records")

        # Step 5: Confirm old Topshiriq 4 data is completely removed and new 85 records used
        print("\n--- STEP 5: Confirm Topshiriq 4 Contains ONLY 85 Records (NOT 120 + 85 = 205) ---")
        task4_db_count = db.query(Task).filter(Task.source_id == "task_4").count()
        print(f"Topshiriq 4 DB count after replacement: {task4_db_count}")
        assert task4_db_count == 85, f"Expected exactly 85 records for task_4, got {task4_db_count}"

        # Step 6: Confirm other 7 tasks remain 100% unchanged
        print("\n--- STEP 6: Confirm Other 7 Tasks Remain Unchanged ---")
        for sid, expected_count in task_counts.items():
            if sid == "task_4":
                continue
            actual_count = db.query(Task).filter(Task.source_id == sid).count()
            print(f"Checking {sid}: expected {expected_count}, got {actual_count}")
            assert actual_count == expected_count, f"{sid} was affected! Expected {expected_count}, got {actual_count}"
        print("[PASS] All other 7 tasks are 100% intact and unchanged!")

        # Step 7: Confirm Umumiy Svod is recalculated correctly (no old data added to new data)
        print("\n--- STEP 7: Confirm Umumiy Svod Recalculation ---")
        # Expected: 210 - 120 + 85 = 175
        expected_new_svod = sum(task_counts.values()) - 120 + 85
        actual_total_db = db.query(Task).count()
        print(f"Expected new Svod total: {expected_new_svod}, Actual DB total: {actual_total_db}")
        assert actual_total_db == expected_new_svod, f"Expected {expected_new_svod}, got {actual_total_db}"

        new_svod_summary = get_summary(db=db)
        assert new_svod_summary.jami_topshiriqlar == expected_new_svod
        print(f"[PASS] Recalculated Umumiy Svod: {new_svod_summary.jami_topshiriqlar} total tasks")

        # Step 8: Test invalid file upload for task_2 (Requirement 13)
        print("\n--- STEP 8: Test Invalid Excel Upload for task_2 (Resilience & No Data Loss) ---")
        corrupted_bytes = b"Corrupted invalid spreadsheet content"
        res_invalid = upload_and_replace_task_excel(db, "task_2", "invalid_corrupted.xlsx", corrupted_bytes)
        assert res_invalid["success"] == False, "Invalid file should return success=False"
        
        # Verify previous 15 records of task_2 are preserved
        task2_count_after_fail = db.query(Task).filter(Task.source_id == "task_2").count()
        assert task2_count_after_fail == 15, f"task_2 data was corrupted! Count: {task2_count_after_fail}"
        assert os.path.exists(get_task_current_excel_path("task_2")), "task_2 current.xlsx should NOT be deleted"
        print("[PASS] Invalid upload rejected, task_2 preserved previous valid 15 records and current.xlsx!")

        # Step 9: Test Delete control for task_8 (Requirement 11)
        print("\n--- STEP 9: Test Delete Control for task_8 ---")
        del_res = delete_task_source(db, "task_8")
        assert del_res["success"] == True
        task8_count = db.query(Task).filter(Task.source_id == "task_8").count()
        assert task8_count == 0, f"task_8 records should be 0, got {task8_count}"
        assert not os.path.exists(get_task_current_excel_path("task_8")), "task_8 current.xlsx should be deleted"
        
        svod_after_del = get_summary(db=db)
        expected_after_del = expected_new_svod - 11  # 175 - 11 = 164
        assert svod_after_del.jami_topshiriqlar == expected_after_del
        print(f"[PASS] task_8 deleted cleanly, Umumiy Svod recalculated to {svod_after_del.jami_topshiriqlar}")

        # Step 10: Test Refresh All Task Sources (Requirement 12)
        print("\n--- STEP 10: Test Refresh All Task Sources ---")
        ref_all_res = refresh_all_task_sources(db)
        assert ref_all_res["success"] == True
        assert len(ref_all_res["refreshed_sources"]) == 7  # 7 remaining active tasks
        assert db.query(Task).count() == expected_after_del
        print(f"[PASS] Refresh all succeeded: {len(ref_all_res['refreshed_sources'])} active task sources reread and recalculated!")

        print("\n==================================================================")
        print("ALL SCENARIO CHECKS PASSED WITH 100% SUCCESS!")
        print("==================================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_scenario()
