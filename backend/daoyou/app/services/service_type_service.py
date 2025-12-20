from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.service_type import ServiceType, ServiceTypeCreate
from uuid import uuid4

class ServiceTypeService:
    @staticmethod
    def get_all_service_types(db: Session) -> List[ServiceType]:
        """获取所有服务类型"""
        query = text("""
            SELECT id, key, title, description, icon_name, color, gradient, created_at, updated_at
            FROM service_types
            ORDER BY key
        """)
        result = db.execute(query)
        service_types = []
        for row in result:
            # 确保返回的数据类型与模型定义匹配
            row_dict = dict(row._mapping)
            row_dict['id'] = str(row_dict['id'])  # 将UUID转换为字符串
            service_types.append(ServiceType.model_validate(row_dict))
        return service_types

    @staticmethod
    def get_service_type_by_key(db: Session, key: str) -> Optional[ServiceType]:
        """根据key获取服务类型"""
        query = text("""
            SELECT id, key, title, description, icon_name, color, gradient, created_at, updated_at
            FROM service_types
            WHERE key = :key
        """)
        result = db.execute(query, {"key": key})
        row = result.first()
        if row:
            # 确保返回的数据类型与模型定义匹配
            row_dict = dict(row._mapping)
            row_dict['id'] = str(row_dict['id'])  # 将UUID转换为字符串
            return ServiceType.model_validate(row_dict)
        return None

    @staticmethod
    def create_service_type(db: Session, service_type: ServiceTypeCreate) -> ServiceType:
        """创建新的服务类型"""
        service_id = str(uuid4())
        query = text("""
            INSERT INTO service_types (id, key, title, description, icon_name, color, gradient)
            VALUES (:id, :key, :title, :description, :icon_name, :color, :gradient)
            RETURNING id, key, title, description, icon_name, color, gradient, created_at, updated_at
        """)
        values = {
            "id": service_id,
            "key": service_type.key,
            "title": service_type.title,
            "description": service_type.description,
            "icon_name": service_type.icon_name,
            "color": service_type.color,
            "gradient": service_type.gradient
        }
        result = db.execute(query, values)
        db.commit()
        row = result.first()
        # 确保返回的数据类型与模型定义匹配
        row_dict = dict(row._mapping)
        row_dict['id'] = str(row_dict['id'])  # 将UUID转换为字符串
        return ServiceType.model_validate(row_dict)

    @staticmethod
    def update_service_type(db: Session, key: str, service_type: ServiceTypeCreate) -> Optional[ServiceType]:
        """更新服务类型"""
        query = text("""
            UPDATE service_types
            SET title = :title,
                description = :description,
                icon_name = :icon_name,
                color = :color,
                gradient = :gradient
            WHERE key = :key
            RETURNING id, key, title, description, icon_name, color, gradient, created_at, updated_at
        """)
        values = {
            "key": key,
            "title": service_type.title,
            "description": service_type.description,
            "icon_name": service_type.icon_name,
            "color": service_type.color,
            "gradient": service_type.gradient
        }
        result = db.execute(query, values)
        db.commit()
        row = result.first()
        if row:
            # 确保返回的数据类型与模型定义匹配
            row_dict = dict(row._mapping)
            row_dict['id'] = str(row_dict['id'])  # 将UUID转换为字符串
            return ServiceType.model_validate(row_dict)
        return None

    @staticmethod
    def delete_service_type(db: Session, key: str) -> bool:
        """删除服务类型"""
        query = text("""
            DELETE FROM service_types
            WHERE key = :key
        """)
        result = db.execute(query, {"key": key})
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def initialize_default_service_types(db: Session) -> None:
        """初始化默认服务类型数据 - 基于十天干职业专长"""
        default_types = [
            {
                "key": "jia_wood",
                "title": "甲木道友",
                "description": "喜欢传统文化，尤其奇门遁甲与传统时空观的关系！",
                "icon_name": "CalendarOutlined",
                "color": "#52c41a",
                "gradient": "linear-gradient(135deg, #52c41a 0%, #95de64 100%)"
            },
            {
                "key": "gui_water",
                "title": "癸水道友",
                "description": "喜欢命理八字，尤其八字与天人合一的观念统一性！",
                "icon_name": "HeartOutlined",
                "color": "#eb2f96",
                "gradient": "linear-gradient(135deg, #eb2f96 0%, #f759ab 100%)"
            }
        ]
        
        # 检查是否已存在数据
        query = text("SELECT COUNT(*) FROM service_types")
        result = db.execute(query)
        count = result.scalar()
        
        if count == 0:
            # 批量插入默认数据
            for service_type in default_types:
                ServiceTypeService.create_service_type(
                    db, 
                    ServiceTypeCreate(
                        key=service_type["key"],
                        title=service_type["title"],
                        description=service_type["description"],
                        icon_name=service_type["icon_name"],
                        color=service_type["color"],
                        gradient=service_type["gradient"]
                    )
                )