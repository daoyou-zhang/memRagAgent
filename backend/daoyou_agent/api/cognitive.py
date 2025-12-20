"""Cognitive API for DaoyouAgent.

This module exposes the main HTTP entrypoint for cognitive processing and
delegates the heavy lifting to `CognitiveController`, which in turn uses
the memRag-backed ContextAggregator and AI service adapter.

支持两种响应模式：
- stream=false（默认）: 返回完整 JSON 响应
- stream=true: 返回 SSE 流式响应

认证：
- AUTH_ENABLED=false: 开发模式，不需要认证
- AUTH_ENABLED=true: 生产模式，需要 API Key

凭证传递：
- 用户的 API Key 和 project_id 会传递给 Memory/Knowledge 服务
- 保持用户级别的租户隔离
"""
import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

# 添加 shared 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.auth import get_api_key_from_fastapi_request

from ..models.cognitive import CognitiveRequest, CognitiveResponse
from ..services.cognitive_controller import get_cognitive_controller


router = APIRouter()

_controller = get_cognitive_controller()


@router.post("/process")
async def process_cognitive_request(
    request: CognitiveRequest,
    raw_request: Request,
):
    """Process a cognitive request via Daoyou's cognitive controller.

    当前流程：
    - 接收统一的 `CognitiveRequest`（支持记忆、RAG、工具等控制参数）
    - stream=false: 返回完整 CognitiveResponse（兼容现有调用）
    - stream=true: 返回 SSE 流式响应
    
    凭证传递：
    - 用户的 API Key 会传递给 Memory/Knowledge 服务
    - 保持用户级别的租户隔离
    """
    # 提取用户的 API Key 用于传递给内部服务
    user_api_key = get_api_key_from_fastapi_request(raw_request)
    user_project_id = raw_request.headers.get("X-Project-Id") or request.project_id
    
    try:
        if request.stream:
            # 流式响应
            return StreamingResponse(
                _controller.process_request_stream(request, user_api_key=user_api_key, user_project_id=user_project_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 普通响应（保持兼容）
            return await _controller.process_request(request, user_api_key=user_api_key, user_project_id=user_project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"认知处理失败: {exc}") from exc
