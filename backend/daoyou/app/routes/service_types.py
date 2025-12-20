from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.service_type import ServiceType, ServiceTypeCreate
from ..services.service_type_service import ServiceTypeService

router = APIRouter(
    prefix="/service-types",
    tags=["service-types"],
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=List[ServiceType])
async def get_service_types(db: Session = Depends(get_db)):
    """获取所有服务类型"""
    return ServiceTypeService.get_all_service_types(db)

@router.get("/{key}", response_model=ServiceType)
async def get_service_type(key: str, db: Session = Depends(get_db)):
    """根据key获取服务类型"""
    service_type = ServiceTypeService.get_service_type_by_key(db, key)
    if service_type is None:
        raise HTTPException(status_code=404, detail=f"Service type with key {key} not found")
    return service_type

@router.post("", response_model=ServiceType)
async def create_service_type(service_type: ServiceTypeCreate, db: Session = Depends(get_db)):
    """创建新的服务类型"""
    existing = ServiceTypeService.get_service_type_by_key(db, service_type.key)
    if existing:
        raise HTTPException(status_code=400, detail=f"Service type with key {service_type.key} already exists")
    return ServiceTypeService.create_service_type(db, service_type)

@router.put("/{key}", response_model=ServiceType)
async def update_service_type(key: str, service_type: ServiceTypeCreate, db: Session = Depends(get_db)):
    """更新服务类型"""
    updated = ServiceTypeService.update_service_type(db, key, service_type)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Service type with key {key} not found")
    return updated

@router.delete("/{key}")
async def delete_service_type(key: str, db: Session = Depends(get_db)):
    """删除服务类型"""
    success = ServiceTypeService.delete_service_type(db, key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service type with key {key} not found")
    return {"message": f"Service type with key {key} deleted successfully"}