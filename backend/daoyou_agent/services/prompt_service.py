"""Prompt 配置服务

提供 Prompt 配置的 CRUD 操作，使用 PostgreSQL 数据库
表结构: prompt_configs（在 knowledge 数据库）
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.prompt_config import PromptConfigCreate, PromptConfigUpdate, PromptConfigResponse


def _get_db_url() -> str:
    """获取数据库连接 URL"""
    return os.getenv("KNOWLEDGE_DB_URL") or os.getenv("DATABASE_URL") or \
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', '')}@" \
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'memrag')}"


class PromptService:
    """Prompt 配置管理服务（数据库版）"""
    
    def _get_conn(self):
        """获取数据库连接"""
        return psycopg2.connect(_get_db_url())
    
    def list_all(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    sql = "SELECT * FROM prompt_configs"
                    if enabled_only:
                        sql += " WHERE enabled = true"
                    sql += " ORDER BY priority DESC, created_at DESC"
                    cur.execute(sql)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"查询 Prompt 配置失败: {e}")
            return []
    
    def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM prompt_configs WHERE id = %s", (config_id,))
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"查询 Prompt 配置失败: {e}")
            return None
    
    def get_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        """根据行业获取配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM prompt_configs WHERE category = %s AND enabled = true ORDER BY priority DESC LIMIT 1",
                        (category,)
                    )
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"查询行业 Prompt 失败: {e}")
            return None
    
    def get_by_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """根据项目获取配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM prompt_configs WHERE project_id = %s AND enabled = true ORDER BY priority DESC LIMIT 1",
                        (project_id,)
                    )
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"查询项目 Prompt 失败: {e}")
            return None
    
    def create(self, data: PromptConfigCreate) -> Optional[Dict[str, Any]]:
        """创建配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        INSERT INTO prompt_configs 
                        (category, project_id, name, description, 
                         intent_system_prompt, intent_user_template,
                         response_system_prompt, response_user_template,
                         enabled, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (
                        data.category, data.project_id, data.name, data.description,
                        data.intent_system_prompt, data.intent_user_template,
                        data.response_system_prompt, data.response_user_template,
                        data.enabled, data.priority
                    ))
                    row = cur.fetchone()
                    conn.commit()
                    logger.info(f"创建 Prompt 配置: {data.name}")
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"创建 Prompt 配置失败: {e}")
            raise
    
    def update(self, config_id: int, data: PromptConfigUpdate) -> Optional[Dict[str, Any]]:
        """更新配置"""
        try:
            # 构建动态 UPDATE 语句
            update_fields = []
            values = []
            for field, value in data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                return self.get_by_id(config_id)
            
            values.append(config_id)
            sql = f"UPDATE prompt_configs SET {', '.join(update_fields)}, updated_at = NOW() WHERE id = %s RETURNING *"
            
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, values)
                    row = cur.fetchone()
                    conn.commit()
                    logger.info(f"更新 Prompt 配置: {config_id}")
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"更新 Prompt 配置失败: {e}")
            raise
    
    def delete(self, config_id: int) -> bool:
        """删除配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM prompt_configs WHERE id = %s", (config_id,))
                    deleted = cur.rowcount > 0
                    conn.commit()
                    if deleted:
                        logger.info(f"删除 Prompt 配置: {config_id}")
                    return deleted
        except Exception as e:
            logger.error(f"删除 Prompt 配置失败: {e}")
            return False


# 全局单例
_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """获取 Prompt 服务单例"""
    global _service
    if _service is None:
        _service = PromptService()
    return _service
