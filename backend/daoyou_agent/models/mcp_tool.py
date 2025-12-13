"""道友认知服务 - MCP 工具数据模型

定义工具相关的数据结构：
- ToolDefinition: 工具定义（从数据库读取或代码预设）
- ToolCall: 工具调用请求
- ToolResult: 工具执行结果
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ToolScope(str, Enum):
    """工具作用域"""
    SYSTEM = "system"      # 系统级，所有用户可用
    PROJECT = "project"    # 项目级，指定项目可用
    USER = "user"          # 用户级，指定用户可用


class ToolHandlerType(str, Enum):
    """工具执行器类型"""
    LOCAL = "local"        # 本地函数调用
    HTTP = "http"          # HTTP API 调用
    MCP = "mcp"            # MCP 协议调用


class ToolCategory(str, Enum):
    """工具分类"""
    GENERAL = "general"        # 通用工具
    DIVINATION = "divination"  # 占卜命理
    SEARCH = "search"          # 搜索检索
    UTILITY = "utility"        # 实用工具


class ToolDefinition(BaseModel):
    """工具定义
    
    描述一个工具的基本信息、参数规范、权限范围和执行方式。
    """
    id: Optional[int] = None
    name: str = Field(..., description="工具唯一标识")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="工具描述（给 LLM 看）")
    category: ToolCategory = Field(default=ToolCategory.GENERAL, description="工具分类")
    
    # 参数定义（JSON Schema）
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数 JSON Schema")
    
    # 权限控制
    scope: ToolScope = Field(default=ToolScope.SYSTEM, description="作用域")
    project_ids: List[str] = Field(default_factory=list, description="可用项目列表")
    user_ids: List[str] = Field(default_factory=list, description="可用用户列表")
    
    # 执行配置
    handler_type: ToolHandlerType = Field(default=ToolHandlerType.LOCAL, description="执行器类型")
    handler_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    
    # 状态
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, description="优先级")
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_llm_description(self) -> str:
        """生成给 LLM 看的工具描述
        
        用于让 LLM 决定是否使用这个工具。
        """
        params_desc = ""
        if self.parameters and "properties" in self.parameters:
            props = self.parameters.get("properties", {})
            required = self.parameters.get("required", [])
            params_list = []
            for name, spec in props.items():
                req = "必填" if name in required else "可选"
                desc = spec.get("description", "")
                params_list.append(f"  - {name}（{req}）: {desc}")
            params_desc = "\n".join(params_list)
        
        return f"""工具名称: {self.name}
显示名称: {self.display_name}
描述: {self.description}
参数:
{params_desc}"""


class ToolCall(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")
    
    # 调用上下文
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 调用元信息
    call_id: Optional[str] = Field(default=None, description="调用 ID（用于追踪）")


class ToolResult(BaseModel):
    """工具执行结果"""
    tool_name: str = Field(..., description="工具名称")
    call_id: Optional[str] = Field(default=None, description="调用 ID")
    
    # 执行结果
    success: bool = Field(default=True, description="是否成功")
    result: Any = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    
    # 性能指标
    execution_time: float = Field(default=0.0, description="执行耗时（秒）")
    
    def to_llm_context(self) -> str:
        """生成给 LLM 的上下文信息
        
        用于将工具结果融入回复生成。
        """
        if not self.success:
            return f"【工具调用失败】{self.tool_name}: {self.error}"
        
        if isinstance(self.result, dict):
            # 尝试格式化 dict 结果
            import json
            result_str = json.dumps(self.result, ensure_ascii=False, indent=2)
        else:
            result_str = str(self.result)
        
        return f"【工具结果】{self.tool_name}:\n{result_str}"


class ToolCallDecision(BaseModel):
    """LLM 的工具调用决策
    
    由 LLM 分析用户输入后，决定是否需要调用工具。
    """
    should_call: bool = Field(default=False, description="是否需要调用工具")
    tool_name: Optional[str] = Field(default=None, description="要调用的工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    reasoning: str = Field(default="", description="决策理由")


__all__ = [
    "ToolScope",
    "ToolHandlerType", 
    "ToolCategory",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ToolCallDecision",
]
