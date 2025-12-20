from sqlalchemy.orm import Session
from ..core.database import SessionLocal
from ..services.service_type_service import ServiceTypeService

def init_service_types():
    """初始化服务类型数据"""
    db = SessionLocal()
    try:
        ServiceTypeService.initialize_default_service_types(db)
        print("Service types initialized successfully")
    finally:
        db.close()