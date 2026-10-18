import os
import time
import threading
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .database import SessionLocal
from .excel_reader import read_and_sync_excel, EXCEL_PATH

logger = logging.getLogger("excel_watcher")

class SyncStateManager:
    """Thread-safe synchronization status manager."""
    def __init__(self):
        self._lock = threading.Lock()
        self.is_syncing = False
        self.status = "idle"  # idle, syncing, success, error
        self.message = "Ma'lumotlar yangilandi"
        self.last_updated = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.last_sync_success = True
        self.error_detail = None
        self.total_rows = 0
        self.synced_rows = 0

    def set_syncing(self):
        with self._lock:
            self.is_syncing = True
            self.status = "syncing"
            self.message = "Yangilanmoqda..."

    def set_success(self, total: int, synced: int, timestamp: str = None):
        with self._lock:
            self.is_syncing = False
            self.status = "success"
            self.last_sync_success = True
            self.message = "Ma'lumotlar yangilandi"
            self.total_rows = total
            self.synced_rows = synced
            if timestamp:
                self.last_updated = timestamp
            else:
                self.last_updated = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            self.error_detail = None

    def set_error(self, err_msg: str):
        with self._lock:
            self.is_syncing = False
            self.status = "error"
            self.last_sync_success = False
            self.message = "Excel ma'lumotlarini yangilashda xatolik"
            self.error_detail = err_msg

    def get_state(self) -> dict:
        with self._lock:
            return {
                "is_syncing": self.is_syncing,
                "status": self.status,
                "message": self.message,
                "last_updated": self.last_updated,
                "error_detail": self.error_detail,
                "total_rows": self.total_rows,
                "synced_rows": self.synced_rows
            }

sync_state = SyncStateManager()

from .main_page_excel_parser import process_and_sync_main_page, MAIN_PAGE_EXCEL_PATH
from .kpi_excel_parser import process_and_sync_kpi, KPI_EXCEL_PATH

class ExcelChangeHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds=1.0):
        super().__init__()
        self.debounce_seconds = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()
        self._changed_source = "ALL"

    def on_modified(self, event):
        self._handle_event(event)

    def on_created(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path).lower()
        if filename.startswith("~$") or filename.startswith(".~") or filename.endswith(".tmp"):
            return

        norm_path = os.path.normpath(event.src_path).lower()
        if "tasks" in norm_path or "uploads" in norm_path or "main_page" in norm_path or "ijro.xlsx" in filename:
            self._changed_source = "MULTI_EXCEL"
        elif "kpi" in norm_path:
            self._changed_source = "KPI"
        else:
            return

        logger.info("Detected change in %s (%s). Debouncing %s seconds...", event.src_path, self._changed_source, self.debounce_seconds)
        sync_state.set_syncing()

        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._trigger_sync)
            self._timer.daemon = True
            self._timer.start()

    def _trigger_sync(self):
        logger.info("Executing debounced synchronization for %s...", self._changed_source)
        db = SessionLocal()
        try:
            now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            if self._changed_source in ["MULTI_EXCEL", "MAIN_PAGE", "ALL"]:
                from .task_sources_manager import refresh_all_task_sources
                r_main = refresh_all_task_sources(db)
                if r_main.get("success"):
                    logger.info("Task sources auto-sync SUCCESS")
            if self._changed_source in ["KPI", "ALL"]:
                r_kpi = process_and_sync_kpi(db)
                if r_kpi.get("success"):
                    logger.info("KPI auto-sync SUCCESS")

            from .models import Task
            total_tasks = db.query(Task).count()
            sync_state.set_success(
                total=total_tasks,
                synced=total_tasks,
                timestamp=now_str
            )
        except Exception as e:
            sync_state.set_error(str(e))
            logger.error("Exception during automatic sync: %s", e)
        finally:
            db.close()

def start_excel_watcher() -> Observer:
    data_dir = os.path.dirname(EXCEL_PATH)
    os.makedirs(data_dir, exist_ok=True)

    event_handler = ExcelChangeHandler(debounce_seconds=1.0)
    observer = Observer()
    observer.schedule(event_handler, path=data_dir, recursive=True)
    observer.daemon = True
    observer.start()
    logger.info("Excel watchdog started for folder: %s (recursive, debouncing 1.0s)", data_dir)
    return observer
