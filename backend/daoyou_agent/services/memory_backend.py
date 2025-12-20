from __future__ import annotations

from typing import Any, Dict, Optional, Protocol
import asyncio
import os

from .memory_client import get_memory_client


class IMemoryBackend(Protocol):
    async def get_full_context(
        self,
        *,
        user_id: Optional[str],
        project_id: Optional[str],
        session_id: Optional[str],
        query: Optional[str] = None,
        recent_message_limit: Optional[int] = None,
        rag_top_k: Optional[int] = None,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取完整认知上下文。"""

    async def record_conversation(
        self,
        *,
        user_id: Optional[str],
        project_id: Optional[str],
        session_id: str,
        raw_query: str,
        optimized_query: Optional[str] = None,
        intent: Optional[Dict[str, Any]] = None,
        tool_used: Optional[str] = None,
        tool_result: Optional[str] = None,
        context_used: Optional[Dict[str, Any]] = None,
        llm_response: str,
        processing_time: float = 0.0,
        auto_generate_memory: bool = True,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录一次对话，用于学习闭环。"""


class HttpMemoryBackend(IMemoryBackend):
    """通过 HTTP 的 memory 实现（保持兼容现有行为）。"""

    def __init__(self) -> None:
        self._client = get_memory_client()

    async def get_full_context(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        return await self._client.get_full_context(
            user_id=kwargs.get("user_id"),
            project_id=kwargs.get("project_id"),
            session_id=kwargs.get("session_id"),
            query=kwargs.get("query"),
            recent_message_limit=kwargs.get("recent_message_limit"),
            rag_top_k=kwargs.get("rag_top_k"),
            user_api_key=kwargs.get("user_api_key"),
        )

    async def record_conversation(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        return await self._client.record_conversation(
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_id"),
            project_id=kwargs.get("project_id"),
            raw_query=kwargs.get("raw_query", ""),
            optimized_query=kwargs.get("optimized_query"),
            intent=kwargs.get("intent"),
            tool_used=kwargs.get("tool_used"),
            tool_result=kwargs.get("tool_result"),
            context_used=kwargs.get("context_used"),
            llm_response=kwargs.get("llm_response", ""),
            processing_time=kwargs.get("processing_time", 0.0),
            auto_generate_memory=kwargs.get("auto_generate_memory", True),
        )


class LocalMemoryBackend(IMemoryBackend):
    """本地 memory 实现：

    - get_full_context 目前返回空上下文（不访问 HTTP），避免在未起服务时出现连接错误。
    - record_conversation 直接调用 memory.services.conversation_service 中的同步逻辑。
    """

    def __init__(self) -> None:
        # 延迟导入，避免在未安装 memory 包时出错
        from memory.services.conversation_service import record_conversation_service

        self._record_service = record_conversation_service

    async def get_full_context(
        self,
        *,
        user_id: Optional[str],
        project_id: Optional[str],
        session_id: Optional[str],
        query: Optional[str] = None,
        recent_message_limit: Optional[int] = None,
        rag_top_k: Optional[int] = None,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 暂时返回一个空上下文结构，后续可以接入本地实现
        return {
            "user_profile": None,
            "working_memory": [],
            "rag_memories": [],
            "knowledge_chunks": [],
            "graph_context": None,
            "debug_info": {"backend": "local", "note": "no HTTP call"},
        }

    async def record_conversation(
        self,
        *,
        user_id: Optional[str],
        project_id: Optional[str],
        session_id: str,
        raw_query: str,
        optimized_query: Optional[str] = None,
        intent: Optional[Dict[str, Any]] = None,
        tool_used: Optional[str] = None,
        tool_result: Optional[str] = None,
        context_used: Optional[Dict[str, Any]] = None,
        llm_response: str,
        processing_time: float = 0.0,
        auto_generate_memory: bool = True,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # record_conversation_service 是同步函数，这里用 to_thread 包一层
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "project_id": project_id,
            "raw_query": raw_query,
            "optimized_query": optimized_query,
            "intent": intent or {},
            "tool_used": tool_used,
            "tool_result": tool_result,
            "context_used": context_used or {},
            "llm_response": llm_response,
            "processing_time": processing_time,
            "auto_generate": auto_generate_memory,
        }

        return await asyncio.to_thread(self._record_service, **payload)


_memory_backend: IMemoryBackend | None = None


def get_memory_backend() -> IMemoryBackend:
    global _memory_backend
    if _memory_backend is None:
        backend_type = os.getenv("MEMORY_BACKEND", "http").lower()
        if backend_type == "local":
            _memory_backend = LocalMemoryBackend()
        else:
            _memory_backend = HttpMemoryBackend()
    return _memory_backend
