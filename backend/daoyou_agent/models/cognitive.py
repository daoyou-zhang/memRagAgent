"""Cognitive data models for DaoyouAgent (migrated from original daoyouAgent).

These models describe cognitive requests/responses, memory types, MCP tools
and common API responses. Logic is intentionally kept identical to the
original implementation so higher-level behaviour stays the same.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    """Memory types."""
    EPISODIC = "episodic"      # 情节记忆
    SEMANTIC = "semantic"      # 语义记忆
    PROCEDURAL = "procedural"  # 程序记忆
    PROFILE = "profile"        # 用户画像


class QualityLevel(str, Enum):
    """Response quality level."""
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"


class CognitiveRequest(BaseModel):
    """Main cognitive request model."""

    input: str = Field(..., description="用户输入内容")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    project_id: Optional[str] = Field(None, description="项目ID（memRag上下文必需）")

    enable_memory: bool = Field(True, description="是否启用记忆检索")
    memory_depth: int = Field(5, ge=1, le=50, description="记忆检索深度")
    memory_types: List[MemoryType] = Field(
        default_factory=lambda: [MemoryType.EPISODIC, MemoryType.SEMANTIC],
        description="记忆类型过滤",
    )

    rag_level: int = Field(3, ge=0, le=5, description="RAG增强级别")
    rag_domains: List[str] = Field(default_factory=list, description="RAG领域限制")
    rag_freshness: str = Field("auto", description="知识新鲜度要求")

    enable_tools: bool = Field(True, description="是否启用MCP工具")
    tool_whitelist: List[str] = Field(default_factory=list, description="工具白名单")
    tool_blacklist: List[str] = Field(default_factory=list, description="工具黑名单")
    max_tool_calls: int = Field(10, ge=1, le=50, description="最大工具调用次数")

    enable_learning: bool = Field(True, description="是否启用学习")
    learning_priority: str = Field("normal", description="学习优先级")

    response_format: str = Field("auto", description="响应格式")
    include_reasoning: bool = Field(False, description="是否包含推理过程")
    include_sources: bool = Field(False, description="是否包含信息源")

    max_response_time: int = Field(30, ge=1, le=300, description="最大响应时间(秒)")
    quality_level: QualityLevel = Field(QualityLevel.BALANCED, description="质量级别")

    # 流式响应（默认 False，不影响现有调用）
    stream: bool = Field(False, description="是否启用流式响应")

    # Prompt 覆盖（可选，不传则使用环境变量或默认值）
    intent_system_prompt: Optional[str] = Field(None, description="意图理解系统 prompt")
    intent_user_prompt: Optional[str] = Field(None, description="意图理解用户 prompt 模板")
    response_system_prompt: Optional[str] = Field(None, description="回复生成系统 prompt")
    response_user_prompt: Optional[str] = Field(None, description="回复生成用户 prompt 模板")

    # 用户自定义模型配置（可选，不传则使用环境变量默认配置）
    model_config_override: Optional[Dict[str, Any]] = Field(
        None, 
        description="用户模型配置覆盖，支持字段: api_base, model_name, api_keys, max_tokens, temperature"
    )


class Intent(BaseModel):
    category: str = Field(..., description="意图类别")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="实体信息")
    query: str = Field(..., description="查询内容")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文")
    summary: Optional[str] = Field(None, description="意图简短总结")
    needs_tool: bool = Field(False, description="是否需要调用工具")
    suggested_tools: List[str] = Field(default_factory=list, description="建议使用的工具")


class ReasoningStep(BaseModel):
    step: int = Field(..., description="步骤序号")
    description: str = Field(..., description="步骤描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    duration: float = Field(..., description="执行时间(秒)")


class Source(BaseModel):
    type: str = Field(..., description="源类型")
    content: str = Field(..., description="源内容")
    confidence: float = Field(..., ge=0.0, le=1.0, description="可信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class PerformanceMetrics(BaseModel):
    total_time: float = Field(..., description="总处理时间")
    memory_retrieval_time: float = Field(0.0, description="记忆检索时间")
    rag_time: float = Field(0.0, description="RAG检索时间")
    tool_execution_time: float = Field(0.0, description="工具执行时间")
    generation_time: float = Field(0.0, description="内容生成时间")
    tokens_used: int = Field(0, description="使用的token数量")
    memory_usage: float = Field(0.0, description="内存使用量(MB)")


class CognitiveResponse(BaseModel):
    content: str = Field(..., description="生成内容")
    intent: Intent = Field(..., description="识别的意图")
    confidence: float = Field(..., ge=0.0, le=1.0, description="整体置信度")

    reasoning_steps: Optional[List[ReasoningStep]] = Field(None, description="推理步骤")
    sources: Optional[List[Source]] = Field(None, description="信息源")
    tool_used: Optional[str] = Field(None, description="使用的工具名称")
    tool_results: Optional[Dict[str, Any]] = Field(None, description="工具执行结果")
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="性能指标")

    processing_time: float = Field(..., description="处理时间")
    tokens_used: int = Field(0, description="使用的token数量")
    ai_service_used: str = Field(..., description="使用的AI服务")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")


class Memory(BaseModel):
    id: str = Field(..., description="记忆ID")
    type: MemoryType = Field(..., description="记忆类型")
    content: str = Field(..., description="记忆内容")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    importance: float = Field(..., ge=0.0, le=1.0, description="重要性")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_accessed: datetime = Field(default_factory=datetime.now, description="最后访问时间")
    access_count: int = Field(0, description="访问次数")

    related_memories: List[str] = Field(default_factory=list, description="相关记忆ID")
    tags: List[str] = Field(default_factory=list, description="标签")
    embeddings: Optional[List[float]] = Field(None, description="向量嵌入")

    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")


class MCPToolConfig(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    category: str = Field(..., description="工具类别")

    input_schema: Dict[str, Any] = Field(..., description="输入模式")
    output_schema: Dict[str, Any] = Field(..., description="输出模式")

    endpoint: str = Field(..., description="工具端点")
    timeout: int = Field(30, ge=1, le=300, description="超时时间")
    retry_count: int = Field(3, ge=0, le=10, description="重试次数")

    average_execution_time: float = Field(0.0, description="平均执行时间")
    success_rate: float = Field(1.0, ge=0.0, le=1.0, description="成功率")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")

    required_permissions: List[str] = Field(default_factory=list, description="所需权限")
    allowed_users: List[str] = Field(default_factory=list, description="允许的用户")


class ToolNeeds(BaseModel):
    required_tools: List[str] = Field(default_factory=list, description="必需工具")
    optional_tools: List[str] = Field(default_factory=list, description="可选工具")
    execution_order: List[str] = Field(default_factory=list, description="执行顺序")
    estimated_time: float = Field(0.0, description="预估执行时间")


class ExecutionPlan(BaseModel):
    parallel_groups: List[List[str]] = Field(default_factory=list, description="并行执行组")
    estimated_time: float = Field(0.0, description="预估总时间")
    fallback_plan: List[str] = Field(default_factory=list, description="备用方案")


class APIResponse(BaseModel):
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
