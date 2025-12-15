"""道友认知服务 - 工具编排器

职责：
- 根据意图分析结果，决定是否需要调用工具
- 让 LLM 选择合适的工具并填充参数
- 执行工具并返回结果

调用流程：
1. 意图分析返回 needs_tool=true
2. 获取可用工具列表
3. LLM 决策：选择工具 + 填参数
4. 执行工具
5. 返回结果供回复生成使用
"""
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from ..models.mcp_tool import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    ToolCallDecision,
)
from ..models.cognitive import Intent
from .tool_registry import get_tool_registry
from .tool_executor import get_tool_executor
from .ai_service_adapter import get_intent_client


# ============================================================
# 工具决策 Prompt
# ============================================================

TOOL_DECISION_SYSTEM_PROMPT = """你是一个工具调用决策专家。

根据当前【用户问题】以及【上下文摘要】（其中包含最近对话和用户画像信息），
判断是否需要调用工具；如果需要，则选择最合适的工具并填充参数。

输出格式（必须是合法 JSON）：
```json
{
  "should_call": true或false,
  "tool_name": "工具名称，不调用时为null",
  "arguments": {"参数名": "参数值"},
  "reasoning": "决策理由"
}
```

注意：
1. 只有当用户的需求需要工具功能时才调用
2. 参数可以从【当前用户问题】以及【上下文摘要】中提取，不要凭空编造
3. 如果必需的信息在当前问题和上下文中都不存在，在 reasoning 中说明缺少什么
4. 日期时间要转换为正确格式
5. 性别参数：男/男生/男性/先生 → "male"，女/女生/女性/女士 → "female"
6. 时间格式：如"4点30"或"4:30"或"4.30" → "04"（取小时）
7. 如果上下文中已经包含了出生日期、时间、性别、出生地点等关键信息，则视为信息完整，可以调用对应工具（如八字排盘）"""

TOOL_DECISION_USER_PROMPT = """用户问题：{user_input}

上下文摘要（最近对话/画像，可选）：
{context_summary}

意图分析：
- 类别：{intent_category}
- 实体：{entities}

可用工具：
{tools_description}

请根据用户问题和上下文，决定是否需要调用工具，输出 JSON："""


class ToolOrchestrator:
    """工具编排器
    
    负责协调工具的发现、决策和执行。
    """

    def __init__(self) -> None:
        """初始化工具编排器"""
        self._registry = get_tool_registry()
        self._executor = get_tool_executor()
        self._llm_client = get_intent_client()  # 用快速模型做决策
        logger.info("工具编排器初始化完成")

    async def process(
        self,
        user_input: str,
        intent: Intent,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ToolResult]:
        """处理工具调用
        
        Args:
            user_input: 用户输入
            intent: 意图分析结果
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID
            
        Returns:
            工具执行结果，如果不需要调用则返回 None
        """
        # 1. 检查是否需要工具
        if not intent.needs_tool:
            logger.debug("意图分析显示不需要工具")
            return None
        
        # 2. 获取可用工具
        tools = await self._registry.get_available_tools(
            user_id=user_id,
            project_id=project_id,
            enabled_only=True,
        )
        
        if not tools:
            logger.warning("没有可用的工具")
            return None
        
        logger.info(f"找到 {len(tools)} 个可用工具: {[t.name for t in tools]}")
        
        # 3. LLM 决策
        decision = await self._make_tool_decision(user_input, intent, tools, context=context)
        
        if not decision.should_call:
            logger.info(f"LLM 决定不调用工具: {decision.reasoning}")
            return None
        
        # 4. 获取工具定义
        tool_def = await self._registry.get_tool_by_name(decision.tool_name)
        if not tool_def:
            logger.error(f"工具 {decision.tool_name} 不存在")
            return ToolResult(
                tool_name=decision.tool_name,
                success=False,
                error=f"工具 {decision.tool_name} 不存在",
            )
        
        logger.info(f"决定调用工具: {decision.tool_name}, 参数: {decision.arguments}")
        
        # 5. 构建调用请求
        tool_call = ToolCall(
            tool_name=decision.tool_name,
            arguments=decision.arguments,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
        )
        
        # 6. 执行工具
        result = await self._executor.execute(tool_def, tool_call)
        
        return result

    async def _make_tool_decision(
        self,
        user_input: str,
        intent: Intent,
        tools: List[ToolDefinition],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolCallDecision:
        """让 LLM 决定是否调用工具
        
        Args:
            user_input: 用户输入
            intent: 意图分析结果
            tools: 可用工具列表
            
        Returns:
            工具调用决策
        """
        # 构建工具描述
        tools_desc = self._registry.get_tools_for_llm(tools)
        
        # 构建实体描述
        entities_desc = "无"
        if intent.entities:
            entities_list = []
            for e in intent.entities:
                if isinstance(e, dict):
                    entities_list.append(f"- {e.get('type', '?')}: {e.get('value', '?')}")
                else:
                    entities_list.append(f"- {e}")
            entities_desc = "\n".join(entities_list)
        
        # 构建上下文摘要（只取最近几条对话和简单画像）
        context_summary = "无"
        if context:
            parts = []
            profile = context.get("user_profile")
            if profile:
                parts.append("[画像] 已有用户画像信息")

            wm = context.get("working_memory") or []
            if wm:
                recent = []
                for m in wm[-3:]:  # 只看最近 3 条
                    role = m.get("role", "?")
                    content = m.get("content", "")[:80]
                    recent.append(f"- {role}: {content}")
                parts.append("[最近对话]\n" + "\n".join(recent))

            if parts:
                context_summary = "\n".join(parts)

        # 构建 prompt
        user_prompt = TOOL_DECISION_USER_PROMPT.format(
            user_input=user_input,
            context_summary=context_summary,
            intent_category=intent.category,
            entities=entities_desc,
            tools_description=tools_desc,
        )
        
        messages = [
            {"role": "system", "content": TOOL_DECISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            response = await self._llm_client.generate(messages, temperature=0.1)
            decision = self._parse_decision(response)
            return decision
        except Exception as exc:
            logger.error(f"工具决策失败: {exc}")
            return ToolCallDecision(
                should_call=False,
                reasoning=f"决策过程出错: {exc}",
            )

    def _parse_decision(self, response: str) -> ToolCallDecision:
        """解析 LLM 的决策响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return ToolCallDecision(
                    should_call=data.get("should_call", False),
                    tool_name=data.get("tool_name"),
                    arguments=data.get("arguments", {}),
                    reasoning=data.get("reasoning", ""),
                )
        except json.JSONDecodeError as e:
            logger.warning(f"解析工具决策 JSON 失败: {e}")
        
        # 解析失败，默认不调用
        return ToolCallDecision(
            should_call=False,
            reasoning=f"无法解析 LLM 响应: {response[:200]}",
        )

    async def execute_tool_directly(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ToolResult:
        """直接执行指定工具（跳过 LLM 决策）
        
        用于 API 直接调用或测试。
        """
        tool_def = await self._registry.get_tool_by_name(tool_name)
        if not tool_def:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"工具 {tool_name} 不存在",
            )
        
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            project_id=project_id,
        )
        
        return await self._executor.execute(tool_def, tool_call)


# ============================================================
# 全局单例
# ============================================================
_orchestrator_instance: Optional[ToolOrchestrator] = None


def get_tool_orchestrator() -> ToolOrchestrator:
    """获取全局工具编排器实例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ToolOrchestrator()
    return _orchestrator_instance


__all__ = ["ToolOrchestrator", "get_tool_orchestrator"]
