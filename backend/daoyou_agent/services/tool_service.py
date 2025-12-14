"""工具数据库服务

提供 MCP 工具的数据库 CRUD 操作
表结构: mcp_tools
"""
import os
from typing import Optional, List, Dict, Any
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.mcp_tool import ToolDefinition, ToolCategory, ToolScope, ToolHandlerType


def _get_db_url() -> str:
    """获取数据库连接 URL"""
    return os.getenv("KNOWLEDGE_DB_URL") or os.getenv("DATABASE_URL") or \
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', '')}@" \
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'memrag')}"


class ToolService:
    """工具数据库服务"""
    
    def _get_conn(self):
        """获取数据库连接"""
        return psycopg2.connect(_get_db_url())
    
    def _row_to_dict(self, row: dict) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "id": row["id"],
            "name": row["name"],
            "display_name": row["display_name"],
            "description": row["description"],
            "category": row["category"],
            "parameters": row["parameters"] or {},
            "scope": row["scope"],
            "project_ids": row.get("project_ids") or [],
            "user_ids": row.get("user_ids") or [],
            "handler_type": row["handler_type"],
            "handler_config": row["handler_config"] or {},
            "enabled": row["enabled"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    
    def list_all(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """获取所有工具"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    sql = "SELECT * FROM mcp_tools"
                    if enabled_only:
                        sql += " WHERE enabled = true"
                    sql += " ORDER BY priority DESC, name ASC"
                    cur.execute(sql)
                    return [self._row_to_dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"查询工具列表失败: {e}")
            return []
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM mcp_tools WHERE name = %s", (name,))
                    row = cur.fetchone()
                    return self._row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"查询工具失败: {e}")
            return None
    
    def get_by_id(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取工具"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM mcp_tools WHERE id = %s", (tool_id,))
                    row = cur.fetchone()
                    return self._row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"查询工具失败: {e}")
            return None
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建工具"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        INSERT INTO mcp_tools 
                        (name, display_name, description, category, parameters,
                         scope, project_ids, user_ids, handler_type, handler_config,
                         enabled, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (
                        data["name"],
                        data["display_name"],
                        data["description"],
                        data.get("category", "general"),
                        psycopg2.extras.Json(data.get("parameters", {})),
                        data.get("scope", "system"),
                        data.get("project_ids", []),
                        data.get("user_ids", []),
                        data.get("handler_type", "local"),
                        psycopg2.extras.Json(data.get("handler_config", {})),
                        data.get("enabled", True),
                        data.get("priority", 0),
                    ))
                    row = cur.fetchone()
                    conn.commit()
                    logger.info(f"创建工具: {data['name']}")
                    return self._row_to_dict(row) if row else None
        except psycopg2.errors.UniqueViolation:
            logger.warning(f"工具已存在: {data['name']}")
            raise ValueError(f"工具 '{data['name']}' 已存在")
        except Exception as e:
            logger.error(f"创建工具失败: {e}")
            raise
    
    def update(self, name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新工具"""
        try:
            # 构建动态 UPDATE 语句
            update_fields = []
            values = []
            
            field_mapping = {
                "display_name": "display_name",
                "description": "description",
                "category": "category",
                "parameters": "parameters",
                "scope": "scope",
                "project_ids": "project_ids",
                "user_ids": "user_ids",
                "handler_type": "handler_type",
                "handler_config": "handler_config",
                "enabled": "enabled",
                "priority": "priority",
            }
            
            for key, db_field in field_mapping.items():
                if key in data and data[key] is not None:
                    if key in ["parameters", "handler_config"]:
                        update_fields.append(f"{db_field} = %s")
                        values.append(psycopg2.extras.Json(data[key]))
                    else:
                        update_fields.append(f"{db_field} = %s")
                        values.append(data[key])
            
            if not update_fields:
                return self.get_by_name(name)
            
            values.append(name)
            sql = f"UPDATE mcp_tools SET {', '.join(update_fields)}, updated_at = NOW() WHERE name = %s RETURNING *"
            
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, values)
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        logger.info(f"更新工具: {name}")
                        return self._row_to_dict(row)
                    return None
        except Exception as e:
            logger.error(f"更新工具失败: {e}")
            raise
    
    def delete(self, name: str) -> bool:
        """删除工具"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM mcp_tools WHERE name = %s", (name,))
                    deleted = cur.rowcount > 0
                    conn.commit()
                    if deleted:
                        logger.info(f"删除工具: {name}")
                    return deleted
        except Exception as e:
            logger.error(f"删除工具失败: {e}")
            return False
    
    def toggle_enabled(self, name: str, enabled: bool) -> Optional[Dict[str, Any]]:
        """启用/禁用工具"""
        return self.update(name, {"enabled": enabled})


# 全局单例
_service: Optional[ToolService] = None


def get_tool_service() -> ToolService:
    """获取工具服务单例"""
    global _service
    if _service is None:
        _service = ToolService()
    return _service
