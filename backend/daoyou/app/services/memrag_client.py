import os
import logging
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_MEMRAG_BASE_URL = os.getenv("MEMRAG_BASE_URL", "").rstrip("/")
_MEMRAG_PROJECT_ID = os.getenv("MEMRAG_PROJECT_ID", "my_chat_app")
_MEMRAG_ONCE_PATH = os.getenv("MEMRAG_ONCE_PATH", "/api/cognitive/once")
_MEMRAG_STREAM_PATH = os.getenv("MEMRAG_STREAM_PATH", "/api/cognitive/stream_text")
_MEMRAG_TIMEOUT = float(os.getenv("MEMRAG_TIMEOUT", "60"))

_MEMRAG_API_KEY = os.getenv("MEMRAG_API_KEY") or os.getenv("DAOYOU_API_KEY")
_MEMRAG_INTERNAL = os.getenv("MEMRAG_INTERNAL", "false").lower() == "true"


def _require_base_url() -> str:
    if not _MEMRAG_BASE_URL:
        raise RuntimeError("MEMRAG_BASE_URL 未配置，无法调用 memRagAgent 服务")
    return _MEMRAG_BASE_URL


async def _cognitive_once_internal(
    *,
    input_text: str,
    user_id: str,
    session_id: str,
    agent_id: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        from memRagAgent.backend.daoyou_agent.models.cognitive import CognitiveRequest
        from memRagAgent.backend.daoyou_agent.services.cognitive_controller import get_cognitive_controller
    except Exception as e:
        logger.error("memRagAgent 内部模块导入失败: %s", e, exc_info=True)
        raise

    base_context: Dict[str, Any] = {}
    memory_depth: Optional[int] = None
    rag_level: Optional[int] = None
    enable_tools: Optional[bool] = None
    enable_learning: Optional[bool] = None

    project_id = _MEMRAG_PROJECT_ID

    if extra_payload:
        ctx = extra_payload.get("context")
        if isinstance(ctx, dict):
            base_context = ctx
        if "project_id" in extra_payload and extra_payload["project_id"]:
            project_id = str(extra_payload["project_id"])
        if "memory_depth" in extra_payload:
            try:
                memory_depth = int(extra_payload["memory_depth"])
            except Exception:
                memory_depth = None
        if "rag_level" in extra_payload:
            try:
                rag_level = int(extra_payload["rag_level"])
            except Exception:
                rag_level = None
        if "enable_tools" in extra_payload:
            enable_tools = bool(extra_payload["enable_tools"])
        if "enable_learning" in extra_payload:
            enable_learning = bool(extra_payload["enable_learning"])

    req = CognitiveRequest(
        input=input_text,
        user_id=str(user_id),
        session_id=str(session_id),
        project_id=project_id,
        agent_id=agent_id,
        context=base_context or None,
    )

    if memory_depth is not None:
        req.memory_depth = memory_depth
    if rag_level is not None:
        req.rag_level = rag_level
    if enable_tools is not None:
        req.enable_tools = enable_tools
    if enable_learning is not None:
        req.enable_learning = enable_learning

    controller = get_cognitive_controller()
    resp = await controller.process_request(req, user_api_key=None, user_project_id=project_id)

    intent_json: Optional[Dict[str, Any]] = None
    try:
        if resp.intent is not None:
            intent_json = resp.intent.dict()
    except Exception:
        intent_json = None

    return {
        "output": resp.content,
        "content": resp.content,
        "answer": resp.content,
        "model": resp.ai_service_used,
        "token_usage": {"total": resp.tokens_used},
        "intent_json": intent_json,
    }


async def cognitive_once(
    *,
    input_text: str,
    user_id: str,
    session_id: str,
    agent_id: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if _MEMRAG_INTERNAL:
        try:
            return await _cognitive_once_internal(
                input_text=input_text,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
                extra_payload=extra_payload,
            )
        except Exception as e:
            logger.error("memRagAgent 内部调用失败，回退 HTTP: %s", e, exc_info=True)

    base_url = _require_base_url()
    url = f"{base_url}{_MEMRAG_ONCE_PATH}"

    payload: Dict[str, Any] = {
        "input": input_text,
        "user_id": str(user_id),
        "session_id": str(session_id),
    }
    if agent_id:
        payload["agent_id"] = agent_id
    if extra_payload:
        payload.update(extra_payload)
    if "project_id" not in payload or not payload["project_id"]:
        payload["project_id"] = _MEMRAG_PROJECT_ID

    headers = {}
    if _MEMRAG_API_KEY:
        headers["Authorization"] = f"Bearer {_MEMRAG_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=_MEMRAG_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers or None)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("memRagAgent cognitive_once ok: %s", {"len": len(str(data))})
            return data
    except Exception as e:
        logger.error("调用 memRagAgent cognitive_once 失败: %s", e, exc_info=True)
        raise


async def cognitive_stream_text(
    *,
    input_text: str,
    user_id: str,
    session_id: str,
    agent_id: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    if _MEMRAG_INTERNAL:
        result = await _cognitive_once_internal(
            input_text=input_text,
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            extra_payload=extra_payload,
        )
        text = (
            (result.get("output") if isinstance(result, dict) else None)
            or (result.get("content") if isinstance(result, dict) else None)
            or (result.get("answer") if isinstance(result, dict) else None)
            or ""
        )
        if text:
            yield str(text)
        return

    base_url = _require_base_url()
    url = f"{base_url}{_MEMRAG_STREAM_PATH}"

    payload: Dict[str, Any] = {
        "input": input_text,
        "user_id": str(user_id),
        "session_id": str(session_id),
    }
    if agent_id:
        payload["agent_id"] = agent_id
    if extra_payload:
        payload.update(extra_payload)
    if "project_id" not in payload or not payload["project_id"]:
        payload["project_id"] = _MEMRAG_PROJECT_ID

    headers = {}
    if _MEMRAG_API_KEY:
        headers["Authorization"] = f"Bearer {_MEMRAG_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload, headers=headers or None) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_text():
                    if not chunk:
                        continue
                    yield chunk
    except Exception as e:
        logger.error("调用 memRagAgent cognitive_stream_text 失败: %s", e, exc_info=True)
        raise
