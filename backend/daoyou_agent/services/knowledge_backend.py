from __future__ import annotations

from typing import Any, Dict, Optional, Protocol
import os

from .knowledge_client import get_knowledge_client


class IKnowledgeBackend(Protocol):
    async def rag_query(
        self,
        *,
        query: str,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 5,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """知识库 RAG 查询。"""


class HttpKnowledgeBackend(IKnowledgeBackend):
    """通过 HTTP 的知识库实现（保持兼容现有行为）。"""

    def __init__(self) -> None:
        self._client = get_knowledge_client()

    async def rag_query(
        self,
        *,
        query: str,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 5,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._client.rag_query(
            query=query,
            project_id=project_id,
            domain=domain,
            top_k=top_k,
            user_api_key=user_api_key,
        )


class LocalKnowledgeBackend(IKnowledgeBackend):
    """本地知识库实现占位：

    当前不访问 HTTP 服务，直接返回空 used_chunks 结构，
    主要用于开发环境关闭 knowledge 服务时避免连接错误。
    后续可接入 knowledge.services 中的本地查询逻辑。
    """

    async def rag_query(
        self,
        *,
        query: str,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 5,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "used_chunks": [],
            "debug": {
                "backend": "local",
                "note": "no HTTP call",
            },
        }


_knowledge_backend: IKnowledgeBackend | None = None


def get_knowledge_backend() -> IKnowledgeBackend:
    global _knowledge_backend
    if _knowledge_backend is None:
        backend_type = os.getenv("KNOWLEDGE_BACKEND", "http").lower()
        if backend_type == "local":
            _knowledge_backend = LocalKnowledgeBackend()
        else:
            _knowledge_backend = HttpKnowledgeBackend()
    return _knowledge_backend
