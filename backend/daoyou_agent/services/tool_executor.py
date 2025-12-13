"""道友认知服务 - 工具执行器

职责：
- 执行工具调用
- 支持多种执行方式：本地函数、HTTP API、MCP 协议
- 超时控制和错误处理

使用方式：
    executor = get_tool_executor()
    result = await executor.execute(tool_def, tool_call)
"""
import time
import importlib
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from ..models.mcp_tool import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    ToolHandlerType,
)


class ToolExecutor:
    """工具执行器
    
    根据工具定义的 handler_type 选择合适的执行方式：
    - local: 调用本地 Python 函数
    - http: 调用 HTTP API
    - mcp: 调用 MCP 协议（待实现）
    """

    def __init__(self) -> None:
        """初始化工具执行器"""
        self._local_handlers: Dict[str, Any] = {}  # 缓存本地函数引用
        logger.info("工具执行器初始化完成")

    async def execute(
        self,
        tool_def: ToolDefinition,
        tool_call: ToolCall,
        timeout: float = 30.0,
    ) -> ToolResult:
        """执行工具调用
        
        Args:
            tool_def: 工具定义
            tool_call: 调用请求
            timeout: 超时时间（秒）
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        try:
            if tool_def.handler_type == ToolHandlerType.LOCAL:
                result = await self._execute_local(tool_def, tool_call)
            elif tool_def.handler_type == ToolHandlerType.HTTP:
                result = await self._execute_http(tool_def, tool_call, timeout)
            elif tool_def.handler_type == ToolHandlerType.MCP:
                result = await self._execute_mcp(tool_def, tool_call, timeout)
            else:
                raise ValueError(f"未知的执行器类型: {tool_def.handler_type}")
            
            execution_time = time.time() - start_time
            logger.info(f"工具 {tool_def.name} 执行成功，耗时 {execution_time:.2f}秒")
            
            return ToolResult(
                tool_name=tool_def.name,
                call_id=tool_call.call_id,
                success=True,
                result=result,
                execution_time=execution_time,
            )
            
        except Exception as exc:
            execution_time = time.time() - start_time
            logger.error(f"工具 {tool_def.name} 执行失败: {exc}")
            
            return ToolResult(
                tool_name=tool_def.name,
                call_id=tool_call.call_id,
                success=False,
                error=str(exc),
                execution_time=execution_time,
            )

    async def _execute_local(
        self,
        tool_def: ToolDefinition,
        tool_call: ToolCall,
    ) -> Any:
        """执行本地函数
        
        handler_config 格式:
        {
            "module": "daoyou_agent.tools.bazi",
            "function": "calculate_bazi"
        }
        """
        config = tool_def.handler_config
        module_path = config.get("module", "")
        func_name = config.get("function", "")
        
        if not module_path or not func_name:
            raise ValueError(f"工具 {tool_def.name} 的本地函数配置不完整")
        
        # 获取或导入函数
        cache_key = f"{module_path}.{func_name}"
        if cache_key not in self._local_handlers:
            try:
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
                self._local_handlers[cache_key] = func
            except Exception as exc:
                raise ImportError(f"无法导入工具函数 {cache_key}: {exc}")
        
        func = self._local_handlers[cache_key]
        
        # 调用函数（支持同步和异步）
        import asyncio
        if asyncio.iscoroutinefunction(func):
            result = await func(**tool_call.arguments)
        else:
            result = func(**tool_call.arguments)
        
        return result

    async def _execute_http(
        self,
        tool_def: ToolDefinition,
        tool_call: ToolCall,
        timeout: float,
    ) -> Any:
        """执行 HTTP API 调用
        
        handler_config 格式:
        {
            "url": "https://api.example.com/endpoint",
            "method": "POST",
            "headers": {"Authorization": "Bearer xxx"}
        }
        """
        config = tool_def.handler_config
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        
        if not url:
            raise ValueError(f"工具 {tool_def.name} 的 HTTP URL 未配置")
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(
                    url,
                    params=tool_call.arguments,
                    headers=headers,
                    timeout=timeout,
                )
            elif method == "POST":
                resp = await client.post(
                    url,
                    json=tool_call.arguments,
                    headers=headers,
                    timeout=timeout,
                )
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            resp.raise_for_status()
            return resp.json()

    async def _execute_mcp(
        self,
        tool_def: ToolDefinition,
        tool_call: ToolCall,
        timeout: float,
    ) -> Any:
        """执行 MCP 协议调用（待实现）
        
        handler_config 格式:
        {
            "server": "mcp://localhost:8080",
            "tool_id": "xxx"
        }
        """
        # TODO: 实现 MCP 协议调用
        raise NotImplementedError("MCP 协议调用尚未实现")


# ============================================================
# 全局单例
# ============================================================
_executor_instance: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """获取全局工具执行器实例"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ToolExecutor()
    return _executor_instance


__all__ = ["ToolExecutor", "get_tool_executor"]
