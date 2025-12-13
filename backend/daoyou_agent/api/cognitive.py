"""Cognitive API for DaoyouAgent.

This module exposes the main HTTP entrypoint for cognitive processing and
delegates the heavy lifting to `CognitiveController`, which in turn uses
the memRag-backed ContextAggregator and AI service adapter.

支持两种响应模式：
- stream=false（默认）: 返回完整 JSON 响应
- stream=true: 返回 SSE 流式响应
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models.cognitive import CognitiveRequest, CognitiveResponse
from ..services.cognitive_controller import get_cognitive_controller


router = APIRouter()

_controller = get_cognitive_controller()


@router.post("/process")
async def process_cognitive_request(request: CognitiveRequest):
    """Process a cognitive request via Daoyou's cognitive controller.

    当前流程：
    - 接收统一的 `CognitiveRequest`（支持记忆、RAG、工具等控制参数）
    - stream=false: 返回完整 CognitiveResponse（兼容现有调用）
    - stream=true: 返回 SSE 流式响应
    """
    try:
        if request.stream:
            # 流式响应
            return StreamingResponse(
                _controller.process_request_stream(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 普通响应（保持兼容）
            return await _controller.process_request(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"认知处理失败: {exc}") from exc
