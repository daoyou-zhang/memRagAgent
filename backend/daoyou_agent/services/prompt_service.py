"""Prompt 配置服务

负责从 PostgreSQL 的 prompt_configs 表读写 Prompt 配置。

此模块被认知控制器和 Prompt 管理 API 复用，需保持接口稳定：
- list_all(enabled_only=False)
- get_by_id(id)
- get_by_category(category)
- get_by_project(project_id)
- get_by_agent(agent_id)
- create(PromptConfigCreate)
- update(id, PromptConfigUpdate)
- delete(id)

返回值统一为 dict（直接从 psycopg2 cursor.fetchone()/fetchall() 转换）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.prompt_config import PromptConfigCreate, PromptConfigUpdate


def _get_db_url() -> str:
    """构造数据库连接 URL。

    优先读取专用的 DAOYOU_DB_* 环境变量；
    如未配置，则回退到通用的 POSTGRES_* 配置；
    最后再给出本地默认值，避免硬编码 localhost 导致困惑。
    """

    host = (
        os.getenv("DAOYOU_DB_HOST")
        or os.getenv("POSTGRES_HOST")
        or "localhost"
    )
    port = (
        os.getenv("DAOYOU_DB_PORT")
        or os.getenv("POSTGRES_PORT")
        or "5432"
    )
    user = (
        os.getenv("DAOYOU_DB_USER")
        or os.getenv("POSTGRES_USER")
        or "postgres"
    )
    password = (
        os.getenv("DAOYOU_DB_PASSWORD")
        or os.getenv("POSTGRES_PASSWORD")
        or "postgres"
    )
    database = (
        os.getenv("DAOYOU_DB_NAME")
        or os.getenv("POSTGRES_DB")
        or "daoyou"
    )

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


class PromptService:
    """Prompt 配置的数据库访问服务。"""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.db_url = db_url or _get_db_url()

    # -------------- 内部工具 --------------
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    # -------------- 查询接口 --------------
    def list_all(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM prompt_configs"
        params: List[Any] = []
        if enabled_only:
            sql += " WHERE enabled = true"
        sql += " ORDER BY priority DESC, id ASC"

        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM prompt_configs WHERE id = %s"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (config_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def get_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM prompt_configs WHERE category = %s AND enabled = true ORDER BY priority DESC, id ASC LIMIT 1"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (category,))
            row = cur.fetchone()
        return dict(row) if row else None

    def get_by_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM prompt_configs WHERE project_id = %s AND enabled = true ORDER BY priority DESC, id ASC LIMIT 1"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (project_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def get_by_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """根据 agent_id 获取 Prompt 配置。

        用于为特定人格/智能体绑定专属 Prompt。
        """

        sql = "SELECT * FROM prompt_configs WHERE agent_id = %s AND enabled = true ORDER BY priority DESC, id ASC LIMIT 1"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (agent_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def list_categories(self) -> List[str]:
        """列出所有已存在的 category（去重）。"""

        sql = "SELECT DISTINCT category FROM prompt_configs WHERE category IS NOT NULL AND enabled = true"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return [row["category"] for row in rows if row.get("category")]

    # -------------- 写入接口 --------------
    def create(self, data: PromptConfigCreate) -> Optional[Dict[str, Any]]:
        sql = """
        INSERT INTO prompt_configs (
            category, project_id, agent_id,
            name, description,
            intent_system_prompt, intent_user_template,
            response_system_prompt, response_user_template,
            enabled, priority
        ) VALUES (
            %(category)s, %(project_id)s, %(agent_id)s,
            %(name)s, %(description)s,
            %(intent_system_prompt)s, %(intent_user_template)s,
            %(response_system_prompt)s, %(response_user_template)s,
            %(enabled)s, %(priority)s
        ) RETURNING *
        """
        payload = data.dict()
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, payload)
            row = cur.fetchone()
        return dict(row) if row else None

    def update(self, config_id: int, data: PromptConfigUpdate) -> Optional[Dict[str, Any]]:
        update_fields = {k: v for k, v in data.dict().items() if v is not None}
        if not update_fields:
            return self.get_by_id(config_id)

        set_clauses = []
        params: List[Any] = []
        for idx, (key, value) in enumerate(update_fields.items(), start=1):
            set_clauses.append(f"{key} = %s")
            params.append(value)
        params.append(config_id)

        sql = f"UPDATE prompt_configs SET {', '.join(set_clauses)} WHERE id = %s RETURNING *"

        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return dict(row) if row else None

    def delete(self, config_id: int) -> bool:
        sql = "DELETE FROM prompt_configs WHERE id = %s"
        with self._get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (config_id,))
            return cur.rowcount > 0


_prompt_service_instance: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    global _prompt_service_instance
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
    return _prompt_service_instance
