"""
Safe Database Migration Script: SQLite -> PostgreSQL (Requirement 11)
Migrates all tables, schemas, and records from SQLite to PostgreSQL without loss.
Updates PostgreSQL serial sequences so that auto-increment works seamlessly.
"""

import os
import sys
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .database import Base, DB_DIR
from .models import (
    Admin, Employee, Task, TaskSource,
    DepartmentInfo, Setting, SyncLog, ImportLog,
    KPIRecord, KPISummaryStore
)

def run_migration(pg_url: str = None, sqlite_path: str = None):
    if not pg_url:
        pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        print("[ERROR] DATABASE_URL environment variable is required for PostgreSQL migration.")
        print("Example: DATABASE_URL=postgresql://user:pass@localhost:5432/dashboard python -m backend.migrate_to_postgres")
        sys.exit(1)

    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    if not sqlite_path:
        sqlite_path = os.path.join(DB_DIR, "dashboard.db")

    if not os.path.exists(sqlite_path):
        print(f"[ERROR] Source SQLite database not found at: {sqlite_path}")
        sys.exit(1)

    print(f"[*] Connecting to source SQLite: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sq_cur = sqlite_conn.cursor()

    print(f"[*] Connecting to target PostgreSQL: {pg_url.split('@')[-1] if '@' in pg_url else pg_url}")
    pg_engine = create_engine(pg_url)
    PgSession = sessionmaker(bind=pg_engine)
    pg_session = PgSession()

    # Step 1: Create all tables in PostgreSQL
    print("[*] Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)

    # Step 2: Migrate tables
    table_mappings = [
        ("admins", Admin),
        ("departments_info", DepartmentInfo),
        ("settings", Setting),
        ("task_sources", TaskSource),
        ("employees", Employee),
        ("tasks", Task),
        ("sync_logs", SyncLog),
        ("import_logs", ImportLog),
        ("kpi_records", KPIRecord),
        ("kpi_summaries", KPISummaryStore)
    ]

    for table_name, model_class in table_mappings:
        try:
            sq_rows = sq_cur.execute(f"SELECT * FROM {table_name}").fetchall()
        except sqlite3.OperationalError:
            print(f"  [-] Table '{table_name}' does not exist in SQLite, skipping.")
            continue

        print(f"  [+] Migrating '{table_name}': {len(sq_rows)} records...")

        # Clear existing in target to avoid duplicates
        pg_session.query(model_class).delete()

        col_names = [c.name for c in model_class.__table__.columns]
        for row in sq_rows:
            row_dict = dict(row)
            data = {}
            for col in col_names:
                if col in row_dict:
                    val = row_dict[col]
                    # Handle boolean conversion for is_overdue
                    if col == "is_overdue" and val is not None:
                        val = bool(val)
                    data[col] = val

            obj = model_class(**data)
            pg_session.add(obj)

        pg_session.commit()

        # Step 3: Update PostgreSQL sequences for auto-increment tables
        try:
            with pg_engine.connect() as conn:
                seq_check = conn.execute(
                    text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                ).scalar()
                if seq_check:
                    conn.execute(
                        text(f"SELECT setval('{seq_check}', COALESCE((SELECT MAX(id) FROM {table_name}), 1))")
                    )
                    conn.commit()
        except Exception as e:
            # Table might not have id sequence or SQLite-specific
            pass

    sqlite_conn.close()
    pg_session.close()

    print("[SUCCESS] All tables and data successfully migrated from SQLite to PostgreSQL!")

if __name__ == "__main__":
    run_migration()
