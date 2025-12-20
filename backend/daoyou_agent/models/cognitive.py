"""认知请求与响应的数据模型。

此文件定义了 DaoyouAgent 与外部调用方之间的主要数据结构，
包括 CognitiveRequest / CognitiveResponse 以及中间过程结构。
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆级别控制。"""

    none = "none"           # 不使用记忆
    light = "light"         # 只用轻量近邻记忆
    full = "full"           # 使用完整语义记忆


class QualityLevel(str, Enum):
    """回答质量/成本等级。"""

    fast = "fast"           # 速度优先
    balanced = "balanced"   # 平衡
    high = "high"           # 质量优先


class ReasoningStep(BaseModel):
    """单步推理记录，用于调试和可视化。"""

    step: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Intent(BaseModel):
    """意图分析结果。"""

    category: str = "other"
    confidence: float = 0.0
    entities: List[Dict[str, Any]] = []
    query: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    needs_tool: bool = False
    suggested_tools: List[str] = []


class PerformanceMetrics(BaseModel):
    """简单的性能指标统计。"""

    processing_time: float = 0.0
    tokens_used: int = 0


class CognitiveRequest(BaseModel):
    """认知请求。

    前端和调用方通过该模型与 DaoyouAgent 交互。
    """

    # 基本会话信息
    input: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None

    # Agent / 人格标识
    agent_id: Optional[str] = None

    # 控制选项
    stream: bool = False
    enable_intent: bool = True
    enable_memory: bool = True
    memory_depth: int = 10
    rag_level: int = 0
    enable_tools: bool = True
    enable_learning: bool = True

    # 额外上下文（轻量）
    context: Optional[Dict[str, Any]] = None

    # Prompt 覆盖（请求级最高优先级）
    intent_system_prompt: Optional[str] = None
    intent_user_prompt: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_prompt: Optional[str] = None

    # 兼容历史字段：行业/领域
    industry: Optional[str] = None

    # 用户自定义模型配置（覆盖默认 response 模型）
    model_config_override: Optional[Dict[str, Any]] = None


class CognitiveResponse(BaseModel):
    """认知响应。"""

    content: str
    intent: Optional[Intent] = None
    confidence: float = 0.0

    processing_time: float = 0.0
    ai_service_used: Optional[str] = None
    tokens_used: int = 0

    session_id: Optional[str] = None
    user_id: Optional[str] = None
    tool_used: Optional[str] = None

    reasoning_steps: Optional[List[ReasoningStep]] = None
    metrics: Optional[PerformanceMetrics] = None
