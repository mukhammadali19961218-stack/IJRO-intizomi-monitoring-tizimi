import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

# 1. DATABASE_URL from environment (PostgreSQL for production server)
# Fallback to local SQLite database for local development / testing
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_PATH = os.path.join(DB_DIR, "dashboard.db")
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    is_sqlite = True
else:
    # Handle cloud provider URLs (e.g. postgres:// -> postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # Production PostgreSQL connection pool settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=15,
        max_overflow=25
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def check_and_apply_sqlite_migrations():
    if not is_sqlite:
        return
    import sqlite3
    try:
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("PRAGMA table_info(tasks)")
            cols = [row[1] for row in c.fetchall()]
            if cols:
                if "source_file" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN source_file VARCHAR(255) DEFAULT 'current.xlsx'")
                if "source_id" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN source_id VARCHAR(50) DEFAULT 'task_1'")
                if "deadline_iso" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN deadline_iso VARCHAR(20)")
                if "raw_status" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN raw_status VARCHAR(50)")
                if "employee_id" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN employee_id VARCHAR(50)")
                if "task_type" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN task_type VARCHAR(100)")
                if "topshiriq_turi" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN topshiriq_turi VARCHAR(100)")
                if "hujjat_turi" not in cols:
                    c.execute("ALTER TABLE tasks ADD COLUMN hujjat_turi VARCHAR(100)")
                conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"SQLite migration check note: {e}")

check_and_apply_sqlite_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


