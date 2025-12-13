"""道友认知服务 - 工具注册表

职责：
- 从数据库加载工具定义
- 支持代码预设工具（不依赖数据库）
- 按用户/项目过滤可用工具
- 提供工具发现功能

使用方式：
    registry = get_tool_registry()
    tools = await registry.get_available_tools(user_id="xxx", project_id="yyy")
"""
import os
import json
from typing import Any, Dict, List, Optional
from loguru import logger


def _parse_json_field(value: Any) -> Any:
    """解析可能是字符串的 JSON 字段"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    logger.warning("asyncpg 未安装，工具注册表将仅使用预设工具")

from ..models.mcp_tool import (
    ToolDefinition,
    ToolScope,
    ToolHandlerType,
    ToolCategory,
)


# ============================================================
# 代码预设工具（不依赖数据库）
# ============================================================

PRESET_TOOLS: Dict[str, ToolDefinition] = {
    "bazi_paipan": ToolDefinition(
        name="bazi_paipan",
        display_name="八字排盘",
        description="根据出生时间和地点，计算八字命盘，包括四柱（年柱、月柱、日柱、时柱）、大运、流年、十神、五行平衡等信息。适用于命理分析、运势预测等场景。",
        category=ToolCategory.DIVINATION,
        parameters={
            "type": "object",
            "required": ["year", "month", "day", "hour", "gender", "birth_place"],
            "properties": {
                "year": {"type": "integer", "description": "出生年份（1900-2100）"},
                "month": {"type": "integer", "description": "出生月份（1-12）"},
                "day": {"type": "integer", "description": "出生日期（1-31）"},
                "hour": {"type": "string", "description": "出生小时（00-23）"},
                "minute": {"type": "string", "description": "出生分钟（00-59）", "default": "00"},
                "gender": {"type": "string", "description": "性别", "enum": ["male", "female"]},
                "birth_place": {"type": "string", "description": "出生地点"},
                "calendarType": {"type": "string", "description": "历法类型", "enum": ["solar", "lunar"], "default": "solar"},
                "isLeapMonth": {"type": "boolean", "description": "是否闰月（仅农历有效）", "default": False}
            }
        },
        scope=ToolScope.SYSTEM,
        handler_type=ToolHandlerType.LOCAL,
        handler_config={"module": "daoyou_agent.tools.bazi", "function": "calculate_bazi"},
        enabled=True,
        priority=100,
    ),
    
    # 文件读取工具
    "read_file": ToolDefinition(
        name="read_file",
        display_name="读取文件",
        description="读取指定路径的代码/文本文件内容。支持 Python、JavaScript、TypeScript、Go、Java 等常见编程语言，以及 JSON、YAML、Markdown 等配置和文档文件。用于代码审查、问题排查、代码分析等场景。",
        category=ToolCategory.UTILITY,
        parameters={
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {"type": "string", "description": "文件的绝对路径或相对路径"},
                "encoding": {"type": "string", "description": "文件编码", "default": "utf-8"},
                "max_lines": {"type": "integer", "description": "最大读取行数（不填则读取全部）"},
                "start_line": {"type": "integer", "description": "起始行号（1 开始）", "default": 1},
            }
        },
        scope=ToolScope.SYSTEM,
        handler_type=ToolHandlerType.LOCAL,
        handler_config={"module": "daoyou_agent.tools.file_reader", "function": "read_file"},
        enabled=True,
        priority=90,
    ),
    
    # 目录列表工具
    "list_directory": ToolDefinition(
        name="list_directory",
        display_name="列出目录",
        description="列出指定目录中的文件和子目录。支持通配符匹配和递归搜索。用于了解项目结构、查找文件等场景。",
        category=ToolCategory.UTILITY,
        parameters={
            "type": "object",
            "required": ["dir_path"],
            "properties": {
                "dir_path": {"type": "string", "description": "目录路径"},
                "pattern": {"type": "string", "description": "文件匹配模式（如 *.py）", "default": "*"},
                "recursive": {"type": "boolean", "description": "是否递归子目录", "default": False},
                "max_items": {"type": "integer", "description": "最大返回数量", "default": 100},
            }
        },
        scope=ToolScope.SYSTEM,
        handler_type=ToolHandlerType.LOCAL,
        handler_config={"module": "daoyou_agent.tools.file_reader", "function": "list_directory"},
        enabled=True,
        priority=85,
    ),
}


class ToolRegistry:
    """工具注册表
    
    管理所有可用的工具定义，支持：
    - 代码预设工具（始终可用）
    - 数据库动态工具（需要配置数据库）
    - 按用户/项目过滤
    """

    def __init__(self) -> None:
        """初始化工具注册表"""
        self._preset_tools = PRESET_TOOLS.copy()
        self._db_pool: Optional[Any] = None
        self._db_config = self._load_db_config()
        logger.info(f"工具注册表初始化完成，预设工具数量: {len(self._preset_tools)}")

    def _load_db_config(self) -> Dict[str, str]:
        """加载数据库配置（从环境变量）"""
        return {
            "host": os.getenv("POSTGRES_HOST", "118.178.183.54"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "daoyou"),
            "user": os.getenv("POSTGRES_USER", "daoyou_user"),
            "password": os.getenv("POSTGRES_PASSWORD", ""),
        }

    async def _get_db_pool(self):
        """获取数据库连接池（懒加载）"""
        if not HAS_ASYNCPG:
            return None
            
        if self._db_pool is None:
            try:
                self._db_pool = await asyncpg.create_pool(
                    host=self._db_config["host"],
                    port=int(self._db_config["port"]),
                    database=self._db_config["database"],
                    user=self._db_config["user"],
                    password=self._db_config["password"],
                    min_size=1,
                    max_size=5,
                )
                logger.info("工具注册表数据库连接池创建成功")
            except Exception as exc:
                logger.warning(f"数据库连接失败，仅使用预设工具: {exc}")
                self._db_pool = None
        return self._db_pool

    async def get_available_tools(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[ToolDefinition]:
        """获取可用工具列表
        
        Args:
            user_id: 用户 ID（用于过滤用户级工具）
            project_id: 项目 ID（用于过滤项目级工具）
            category: 工具分类过滤
            enabled_only: 是否只返回启用的工具
            
        Returns:
            符合条件的工具定义列表
        """
        tools: List[ToolDefinition] = []
        
        # 1. 添加预设工具（始终可用）
        for tool in self._preset_tools.values():
            if enabled_only and not tool.enabled:
                continue
            if category and tool.category.value != category:
                continue
            tools.append(tool)
        
        # 2. 从数据库加载动态工具
        db_tools = await self._load_tools_from_db(
            user_id=user_id,
            project_id=project_id,
            category=category,
            enabled_only=enabled_only,
        )
        
        # 3. 合并（数据库优先级高于预设）
        db_tool_names = {t.name for t in db_tools}
        tools = [t for t in tools if t.name not in db_tool_names] + db_tools
        
        # 4. 按优先级排序
        tools.sort(key=lambda t: t.priority, reverse=True)
        
        return tools

    async def _load_tools_from_db(
        self,
        user_id: Optional[str],
        project_id: Optional[str],
        category: Optional[str],
        enabled_only: bool,
    ) -> List[ToolDefinition]:
        """从数据库加载工具"""
        pool = await self._get_db_pool()
        if pool is None:
            return []
        
        try:
            async with pool.acquire() as conn:
                # 构建查询
                query = """
                    SELECT id, name, display_name, description, category,
                           parameters, scope, project_ids, user_ids,
                           handler_type, handler_config, enabled, priority,
                           created_at, updated_at
                    FROM mcp_tools
                    WHERE 1=1
                """
                params = []
                param_idx = 1
                
                if enabled_only:
                    query += f" AND enabled = ${param_idx}"
                    params.append(True)
                    param_idx += 1
                
                if category:
                    query += f" AND category = ${param_idx}"
                    params.append(category)
                    param_idx += 1
                
                # 权限过滤：系统级 OR 匹配的项目/用户
                scope_conditions = ["scope = 'system'"]
                if project_id:
                    scope_conditions.append(f"(scope = 'project' AND ${param_idx} = ANY(project_ids))")
                    params.append(project_id)
                    param_idx += 1
                if user_id:
                    scope_conditions.append(f"(scope = 'user' AND ${param_idx} = ANY(user_ids))")
                    params.append(user_id)
                    param_idx += 1
                
                query += f" AND ({' OR '.join(scope_conditions)})"
                query += " ORDER BY priority DESC"
                
                rows = await conn.fetch(query, *params)
                
                tools = []
                for row in rows:
                    tool = ToolDefinition(
                        id=row["id"],
                        name=row["name"],
                        display_name=row["display_name"],
                        description=row["description"],
                        category=ToolCategory(row["category"]),
                        parameters=_parse_json_field(row["parameters"]),
                        scope=ToolScope(row["scope"]),
                        project_ids=list(row["project_ids"] or []),
                        user_ids=list(row["user_ids"] or []),
                        handler_type=ToolHandlerType(row["handler_type"]),
                        handler_config=_parse_json_field(row["handler_config"]),
                        enabled=row["enabled"],
                        priority=row["priority"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    tools.append(tool)
                
                return tools
                
        except Exception as exc:
            logger.error(f"从数据库加载工具失败: {exc}")
            return []

    async def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """根据名称获取工具定义"""
        # 先查预设
        if name in self._preset_tools:
            return self._preset_tools[name]
        
        # 再查数据库
        pool = await self._get_db_pool()
        if pool is None:
            return None
        
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM mcp_tools WHERE name = $1 AND enabled = true",
                    name
                )
                if row:
                    return ToolDefinition(
                        id=row["id"],
                        name=row["name"],
                        display_name=row["display_name"],
                        description=row["description"],
                        category=ToolCategory(row["category"]),
                        parameters=_parse_json_field(row["parameters"]),
                        scope=ToolScope(row["scope"]),
                        project_ids=list(row["project_ids"] or []),
                        user_ids=list(row["user_ids"] or []),
                        handler_type=ToolHandlerType(row["handler_type"]),
                        handler_config=_parse_json_field(row["handler_config"]),
                        enabled=row["enabled"],
                        priority=row["priority"],
                    )
        except Exception as exc:
            logger.error(f"获取工具 {name} 失败: {exc}")
        
        return None

    def register_preset_tool(self, tool: ToolDefinition) -> None:
        """注册预设工具（代码方式）"""
        self._preset_tools[tool.name] = tool
        logger.info(f"注册预设工具: {tool.name}")

    def get_tools_for_llm(self, tools: List[ToolDefinition]) -> str:
        """生成给 LLM 的工具列表描述"""
        if not tools:
            return "当前没有可用的工具。"
        
        descriptions = []
        for tool in tools:
            descriptions.append(tool.to_llm_description())
        
        return "\n\n".join(descriptions)


# ============================================================
# 全局单例
# ============================================================
_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


__all__ = ["ToolRegistry", "get_tool_registry", "PRESET_TOOLS"]
