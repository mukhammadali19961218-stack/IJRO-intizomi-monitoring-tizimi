from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from .database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="admin", nullable=False)  # 'admin' or 'viewer'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)  # EMP0001, EMP0002...
    full_name = Column(String(255), index=True, nullable=False)
    department = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    photo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"

    # Internal database-generated primary key (Requirement 12)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_type = Column(String(150), nullable=True)
    topshiriq_turi = Column(String(150), nullable=True)
    hujjat_turi = Column(String(150), nullable=True)
    topshiriq = Column(Text, nullable=False)
    boshqarma = Column(String(255), index=True, nullable=True)
    masul = Column(String(255), index=True, nullable=True)
    berilgan_sana = Column(String(50), nullable=True)
    muddat = Column(String(50), index=True, nullable=True)
    deadline_iso = Column(String(20), index=True, nullable=True)
    holat = Column(String(100), index=True, nullable=True)
    bajarilish_foizi = Column(Float, default=0.0)
    ustuvorlik = Column(String(50), index=True, default="Orta")
    izoh = Column(Text, nullable=True)

    # Calculated fields
    days_remaining = Column(Integer, default=0)
    risk_level = Column(String(50), index=True, default="Past")  # Kritik, Yuqori, O'rta, Past
    is_overdue = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source_file = Column(String(255), index=True, default="current.xlsx")
    source_id = Column(String(50), index=True, default="task_1")
    raw_status = Column(String(100), nullable=True)
    employee_id = Column(String(50), index=True, nullable=True)

    __table_args__ = (
        Index("idx_tasks_boshqarma_holat", "boshqarma", "holat"),
        Index("idx_tasks_risk_level", "risk_level"),
        Index("idx_tasks_source_file", "source_file"),
        Index("idx_tasks_source_id", "source_id"),
        Index("idx_tasks_deadline_iso", "deadline_iso"),
        Index("idx_tasks_employee_id", "employee_id"),
    )

class TaskSource(Base):
    __tablename__ = "task_sources"

    id = Column(String(50), primary_key=True, index=True)  # task_1 .. task_8
    name = Column(String(255), nullable=False)
    type = Column(String(50), default="uploaded")
    file_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    sheet_name = Column(String(100), nullable=True)
    header_row = Column(Integer, default=1)
    column_mapping = Column(Text, nullable=True)
    updated_at = Column(String(100), nullable=True)
    status = Column(String(50), default="active")
    error_message = Column(Text, nullable=True)
    total_records = Column(Integer, default=0)

class DepartmentInfo(Base):
    __tablename__ = "departments_info"

    name = Column(String(255), primary_key=True)
    head_name = Column(String(255), nullable=True)
    head_avatar = Column(String(500), nullable=True)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    timestamp = Column(String(100), nullable=True)

class ImportLog(Base):
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_type = Column(String(50), default="MAIN_PAGE", index=True)
    import_time = Column(DateTime, default=datetime.utcnow, index=True)
    total_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    file_name = Column(String(255), default="current.xlsx")
    status = Column(String(50), default="SUCCESS")
    message = Column(Text, nullable=True)

class KPIRecord(Base):
    __tablename__ = "kpi_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    leader_id = Column(Integer, index=True)
    leader_fio = Column(String(200), index=True)
    leader_role = Column(String(200), nullable=True)
    ind_num = Column(Integer, nullable=True)
    ind_title = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    q3_weight = Column(Float, nullable=True)
    q3_plan = Column(Float, nullable=True)
    q3_fact = Column(Float, nullable=True)
    q3_score = Column(Float, nullable=True)
    execution_percent = Column(Float, default=100.0)
    masul_idora = Column(String(200), nullable=True)
    masul_shaxs = Column(String(200), nullable=True)
    masul_telefon = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KPISummaryStore(Base):
    __tablename__ = "kpi_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    q1_score = Column(Float, default=0.0)
    q2_score = Column(Float, default=0.0)
    q3_score = Column(Float, default=0.0)
    cumulative_9m = Column(Float, default=0.0)
    total_leaders = Column(Integer, default=0)
    total_indicators = Column(Integer, default=0)
    completed_indicators = Column(Integer, default=0)
    raw_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

