from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AdminResponse(BaseModel):
    id: int
    username: str
    created_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    id: str
    source_id: Optional[str] = "task_1"
    source_file: Optional[str] = ""
    boshqarma: str
    topshiriq: str
    masul: str
    berilgan_sana: Optional[str] = None
    muddat: str
    holat: str
    bajarilish_foizi: float = 0.0
    ustuvorlik: str = "Orta"
    izoh: Optional[str] = None
    days_remaining: int = 0
    risk_level: str = "Past"
    is_overdue: bool = False

class TaskResponse(TaskBase):
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskSourceSummary(BaseModel):
    jami_topshiriqlar: int = 0
    bajarilgan: int = 0
    jarayonda: int = 0
    boshlanmagan: int = 0
    muddati_otgan: int = 0
    umumiy_bajarilish_foizi: float = 0.0
    kritik_risk: int = 0
    yuqori_risk: int = 0
    orta_risk: int = 0
    past_risk: int = 0

class TaskSourceInfo(BaseModel):
    source_id: str
    name: str
    original_filename: Optional[str] = None
    has_file: bool = False
    uploaded_at: Optional[str] = None
    total_records: int = 0
    summary: Optional[TaskSourceSummary] = None

class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
    page: int
    page_size: int
    total_pages: int

class KPISummary(BaseModel):
    jami_topshiriqlar: int
    bajarilgan: int
    jarayonda: int
    boshlanmagan: int
    muddati_otgan: int
    yuqori_risk: int
    kritik_risk: Optional[int] = 0
    orta_risk: Optional[int] = 0
    past_risk: Optional[int] = 0
    umumiy_bajarilish_foizi: float
    songgi_yangilanish: Optional[str] = None
    sync_status: Optional[str] = "idle"
    sync_message: Optional[str] = "Ma'lumotlar yangilandi"
    is_syncing: Optional[bool] = False

class ColumnMappingRequest(BaseModel):
    filename: str
    mapping: Dict[str, str]

class DepartmentStat(BaseModel):
    boshqarma: str
    jami: int
    bajarilgan: int
    jarayonda: int
    boshlanmagan: int
    muddati_otgan: int
    yuqori_risk: int
    bajarilish_foizi: float
    score: float
    rank: int
    boshliq: Optional[str] = None
    lavozim: Optional[str] = None
    rasm: Optional[str] = None
    tasks: Optional[List[Dict[str, Any]]] = None

class ChartItem(BaseModel):
    name: str
    value: float
    color: Optional[str] = None

class ChartsResponse(BaseModel):
    holat_stats: List[ChartItem]
    boshqarma_foizlari: List[Dict[str, Any]]
    risk_stats: List[ChartItem]
    muddati_otgan_boshqarmalar: List[Dict[str, Any]]

class ImportLogResponse(BaseModel):
    id: int
    import_time: datetime
    total_rows: int
    successful_rows: int
    error_rows: int
    file_name: str
    status: str
    message: Optional[str]

    class Config:
        from_attributes = True
