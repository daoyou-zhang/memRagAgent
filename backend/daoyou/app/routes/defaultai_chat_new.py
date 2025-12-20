"""
新的默认AI聊天路由
演示如何使用新拆分的主模型替换原有调用
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from redis import Redis
from datetime import datetime
import re
import time
import os
import uuid
import logging

from ..core.database import get_db
from ..models.base_chat_schemas import BaseChatRequest
from ..services.auth_service import AuthService
from ..services.rate_limit_service import rate_limit_service
from ..services.memrag_client import cognitive_once, cognitive_stream_text

router = APIRouter(prefix="/chat", tags=["新聊天"])
security = HTTPBearer()
auth_service = AuthService()
logger = logging.getLogger("app.chat")


def get_redis():
    return rate_limit_service.redis


# 已弃用：不再在流式路径做文本清洗，改为通过提示词控制模型署名措辞


def _sse_data_lines(text: str) -> str:
    """将多行文本转换为符合 SSE 规范的多行 data 帧。
    每行以 'data: ' 前缀发送，末尾追加一个空行分隔事件。
    """
    try:
        # 规范化：仅统一换行风格，不压缩多重换行，尽量保留 Markdown 段落
        s = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = s.split("\n")
        if not lines:
            lines = [""]
        # 每行以 data: 开头并换行，调用方负责在事件末尾再追加一个空行
        return "".join([f"data: {line}\n" for line in lines])
    except Exception:
        return f"data: {text}\n"


@router.post("/chat-new")
async def chat_new(
    request: BaseChatRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    新的聊天接口 - 使用拆分后的主模型
    演示如何替换原有的主模型调用
    """
    try:
        # 用户认证（保持不变）
        user = auth_service.get_user_by_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHENTICATED", "redirect": "/login", "message": "无效凭证"},
                headers={"WWW-Authenticate": "Bearer realm=\"daoyou\""}
            )
        
        # 这里不直接调用大模型，仅规范会话 ID 并返回
        session_id = request.key or str(uuid.uuid4())
        return {"session_id": session_id, "data": {}}
            
    except Exception as e:
        logger.error(f"新聊天处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")


@router.post("/chat-direct")
async def chat_direct(
    request: BaseChatRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    直接使用 memRagAgent 进行一次性聊天
    """
    try:
        # 用户认证
        user = auth_service.get_user_by_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHENTICATED", "redirect": "/login", "message": "无效凭证"},
                headers={"WWW-Authenticate": "Bearer realm=\"daoyou\""}
            )

        user_id = str(user.id)
        service_type = request.type or "unknown"
        session_id = request.key or str(uuid.uuid4())

        # 若无问题内容，仅返回会话 ID
        if not request.query or (isinstance(request.query, str) and request.query.strip() == ""):
            return {"session_id": session_id, "data": {}}

        # 调用 memRagAgent 一次性问答
        result = await cognitive_once(
            input_text=request.query,
            user_id=user_id,
            session_id=session_id,
            agent_id=service_type,
            extra_payload={"source": "daoyou_chat_direct"},
        )

        text = (
            (result.get("output") if isinstance(result, dict) else None)
            or (result.get("content") if isinstance(result, dict) else None)
            or (result.get("answer") if isinstance(result, dict) else None)
            or ""
        )

        return {
            "session_id": session_id,
            "data": {
                "role": "assistant",
                "content": text,
                "timestamp": datetime.now().isoformat(),
                "model_info": f"memRagAgent: {result.get('model')}",
                "token_usage": result.get("token_usage", {}),
                "intent_json": result.get("intent_json"),
            },
        }

    except Exception as e:
        logger.error(f"直接聊天处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"直接聊天处理失败: {str(e)}")


@router.api_route("/chat-streaming", methods=["GET", "POST"])
async def chat_streaming(
    raw_request: Request,
    request: BaseChatRequest = None,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    流式聊天接口（SSE）
    将模型生成内容以 Server-Sent Events 的方式持续推送给客户端。
    """
    try:
        # 用户认证
        user = auth_service.get_user_by_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHENTICATED", "redirect": "/login", "message": "无效凭证"},
                headers={"WWW-Authenticate": "Bearer realm=\"daoyou\""}
            )

        # 兼容 GET/POST：GET 从 query 取参，POST 用 body
        if raw_request.method == "GET":
            qp = raw_request.query_params
            request = BaseChatRequest(
                type=qp.get("type"),
                query=qp.get("query"),
                key=qp.get("key"),
            )

        user_id = str(user.id)
        session_id = request.key or str(uuid.uuid4())
        service_type = request.type or "unknown"
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        logger.info(
            f"流式开始 request_id={request_id} 服务类型={service_type} 用户={user_id} 会话={session_id}"
        )

        async def sse_event_generator():
            from json import dumps

            accumulated = ""
            total_chunks = 0

            # 心跳：每15秒发送一次 ping，防止代理空闲断开
            last_beat = time.perf_counter()
            heartbeat_interval = int(os.getenv("SSE_HEARTBEAT_SECONDS", "15"))

            # 立即发送一次启动心跳，避免首包等待过久时前端误判断开
            try:
                yield "event: ping\n" + _sse_data_lines("思考中...") + "\n"
            except Exception:
                pass

            try:
                async for chunk in cognitive_stream_text(
                    input_text=request.query,
                    user_id=user_id,
                    session_id=session_id,
                    agent_id=service_type,
                    extra_payload={"source": "daoyou_chat_streaming"},
                ):
                    # 心跳（即使无增量也保持连接活跃）
                    now = time.perf_counter()
                    if heartbeat_interval > 0 and (now - last_beat) >= heartbeat_interval:
                        last_beat = now
                        yield "event: ping\n" + _sse_data_lines("ping") + "\n"
                    if not chunk:
                        continue
                    total_chunks += 1
                    accumulated += chunk
                    # SSE 数据帧（增量）
                    yield "event: delta\n" + _sse_data_lines(chunk) + "\n"
            except Exception as e:
                err_payload = {
                    "role": "assistant",
                    "content": f"[流式发生异常] {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "model_info": "memRagAgent 流式回复",
                }
                yield "event: final\n" + _sse_data_lines(dumps(err_payload, ensure_ascii=False)) + "\n"
            else:
                if accumulated:
                    final_payload = {
                        "role": "assistant",
                        "content": accumulated,
                        "timestamp": datetime.now().isoformat(),
                        "model_info": "memRagAgent 流式回复",
                    }
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    logger.info(
                        f"流式结束 request_id={request_id} 服务类型={service_type} 用户={user_id} 会话={session_id} 字符数={len(accumulated)} 片段数={total_chunks} 耗时ms={elapsed_ms}"
                    )
                    yield "event: final\n" + _sse_data_lines(dumps(final_payload, ensure_ascii=False)) + "\n"

        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
        }

        return StreamingResponse(sse_event_generator(), media_type="text/event-stream", headers=headers)

    except Exception as e:
        logger.error(f"流式聊天处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"流式聊天处理失败: {str(e)}")


@router.get("/model-info")
async def get_model_info():
    """模型信息占位接口：说明已由 memRagAgent 负责模型配置。

    为保持向后兼容保留此路由，但不再直接访问模型，只返回静态说明。
    """
    return {
        "status": "ok",
        "message": "模型由 memRagAgent 统一管理，本接口仅为兼容保留。",
    }


@router.post("/compare-models")
async def compare_models(
    request: BaseChatRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """模型对比占位接口：原有新旧模型对比逻辑已下线。

    若后续需要，可以在 memRagAgent 内部实现专用对比接口，然后在此转发。
    """
    raise HTTPException(status_code=501, detail="模型对比接口已下线，请直接使用 memRagAgent 接口进行验证。")
