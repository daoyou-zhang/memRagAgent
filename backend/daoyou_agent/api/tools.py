"""工具管理 API

提供 MCP 工具的 CRUD 操作
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.tool_registry import get_tool_registry
from ..models.mcp_tool import ToolDefinition, ToolCategory, ToolScope, ToolHandlerType


router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class ToolCreateRequest(BaseModel):
    """创建工具请求"""
    name: str
    display_name: str
    description: str
    category: str = "general"
    parameters: dict = {}
    scope: str = "system"
    project_ids: List[str] = []
    user_ids: List[str] = []
    handler_type: str = "LOCAL"
    handler_config: dict = {}
    enabled: bool = True
    priority: int = 0


class ToolUpdateRequest(BaseModel):
    """更新工具请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[dict] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class ToolResponse(BaseModel):
    """工具响应"""
    id: Optional[int] = None
    name: str
    display_name: str
    description: str
    category: str
    parameters: dict
    scope: str
    handler_type: str
    enabled: bool
    priority: int


# ============================================================
# API 端点
# ============================================================

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
):
    """获取工具列表"""
    registry = get_tool_registry()
    tools = await registry.get_available_tools(
        user_id=user_id,
        project_id=project_id,
        category=category,
    )
    return [
        ToolResponse(
            id=t.id,
            name=t.name,
            display_name=t.display_name,
            description=t.description,
            category=t.category.value,
            parameters=t.parameters,
            scope=t.scope.value,
            handler_type=t.handler_type.value,
            enabled=t.enabled,
            priority=t.priority,
        )
        for t in tools
    ]


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str):
    """获取单个工具"""
    registry = get_tool_registry()
    tool = await registry.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return ToolResponse(
        id=tool.id,
        name=tool.name,
        display_name=tool.display_name,
        description=tool.description,
        category=tool.category.value,
        parameters=tool.parameters,
        scope=tool.scope.value,
        handler_type=tool.handler_type.value,
        enabled=tool.enabled,
        priority=tool.priority,
    )


@router.post("/", response_model=dict)
async def create_tool(request: ToolCreateRequest):
    """创建工具（需要数据库）"""
    # TODO: 实现数据库写入
    return {
        "success": False,
        "message": "数据库工具创建暂未实现，请直接修改数据库或使用预设工具",
    }


@router.put("/{tool_name}", response_model=dict)
async def update_tool(tool_name: str, request: ToolUpdateRequest):
    """更新工具（需要数据库）"""
    # TODO: 实现数据库更新
    return {
        "success": False,
        "message": "数据库工具更新暂未实现",
    }


@router.delete("/{tool_name}", response_model=dict)
async def delete_tool(tool_name: str):
    """删除工具（需要数据库）"""
    # TODO: 实现数据库删除
    return {
        "success": False,
        "message": "数据库工具删除暂未实现",
    }


@router.get("/categories/list")
async def list_categories():
    """获取工具分类列表"""
    return {
        "categories": [c.value for c in ToolCategory],
    }


@router.post("/{tool_name}/test")
async def test_tool(tool_name: str, params: dict = {}):
    """测试工具调用"""
    from ..services.tool_executor import get_tool_executor
    
    registry = get_tool_registry()
    tool = await registry.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    executor = get_tool_executor()
    result = await executor.execute(tool, params)
    
    return {
        "tool_name": tool_name,
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "execution_time": result.execution_time,
    }
