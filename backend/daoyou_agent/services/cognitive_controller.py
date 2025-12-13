"""道友认知控制器（思维链）

核心认知处理流程：
1. 意图理解 - 使用 LLM 分析用户输入的意图（快速模型 qwen-flash）
2. 工具调用 - 如果需要工具，则调用 MCP 工具系统
3. 上下文聚合 - 通过 memRag 获取用户画像、历史对话、相关记忆
4. 回复生成 - 使用主模型生成回复（高质量模型 deepseek）
5. 学习闭环 - 将对话存入情节记忆，触发画像聚合

架构定位：
- daoyou_agent = 思维链（推理决策）
- memory = 学过的知识（自我学习、自我进化）
- knowledge/RAG = 工具书（知识检索）

自成长能力（已迁移到 memory 服务）：
- ✅ 情节记忆存储：每次对话自动写入 episodic 记忆
- ✅ 画像自动聚合：根据语义增量触发用户画像更新 + 知识提取
- ✅ 自我反省：集成到 profile 聚合流程，复用 LLM 调用
- ✅ 知识进化：提取知识洞察，推送到 knowledge 服务
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import json
import re

from loguru import logger

from ..models.cognitive import (
    CognitiveRequest,
    CognitiveResponse,
    Intent,
    ReasoningStep,
    PerformanceMetrics,
)
from ..config.prompts import get_prompt_config, get_prompt_for_context, PromptConfig
from ..models.mcp_tool import ToolResult
from .context_aggregator import get_context_aggregator
from .ai_service_adapter import get_intent_client, get_response_client, LLMClient
from .memory_client import get_memory_client
from .tool_orchestrator import get_tool_orchestrator


class CognitiveController:
    """核心认知控制器
    
    职责：
    - 协调意图理解、工具调用、上下文聚合、回复生成、学习闭环
    - 支持可配置的 Prompt（请求级、环境变量级、默认值）
    - 分离意图模型和回复模型，可使用不同配置
    - 根据意图自动调用 MCP 工具
    """

    def __init__(self) -> None:
        """初始化认知控制器"""
        self.context_aggregator = get_context_aggregator()
        self.tool_orchestrator = get_tool_orchestrator()  # 工具编排器
        self.intent_client = get_intent_client()      # 意图分析（低温度，如 qwen-flash）
        self.response_client = get_response_client()  # 回复生成（高质量，如 deepseek）
        self.default_prompt_config = get_prompt_config()
        logger.info("道友认知控制器初始化完成（支持 MCP 工具调用）")

    def _get_prompt_config(self, request: CognitiveRequest) -> PromptConfig:
        """获取 prompt 配置，支持请求级别覆盖。"""
        return self.default_prompt_config.override(
            intent_system=request.intent_system_prompt,
            intent_user=request.intent_user_prompt,
            response_system=request.response_system_prompt,
            response_user=request.response_user_prompt,
        )

    async def _understand_intent(
        self,
        user_input: str,
        context: Dict[str, Any],
        prompt_config: PromptConfig,
    ) -> Intent:
        """使用 LLM 分析用户意图。"""
        
        # 构建意图分析的 prompt
        context_str = json.dumps(context, ensure_ascii=False) if context else "{}"
        user_prompt = prompt_config.intent_user_template.format(
            input=user_input,
            context=context_str,
        )

        messages = [
            {"role": "system", "content": prompt_config.intent_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response_text = await self.intent_client.generate(
                messages, temperature=0.1  # 意图分析用低温度保证稳定
            )
            
            # 解析 JSON 响应
            intent_data = self._parse_intent_json(response_text)
            
            return Intent(
                category=intent_data.get("category", "other"),
                confidence=float(intent_data.get("confidence", 0.5)),
                entities=intent_data.get("entities", []),
                query=user_input,
                context=context,
                summary=intent_data.get("summary"),
                needs_tool=intent_data.get("needs_tool", False),
                suggested_tools=intent_data.get("suggested_tools", []),
            )
        except Exception as exc:
            logger.warning(f"意图分析失败，使用默认意图: {exc}")
            return Intent(
                category="other",
                confidence=0.5,
                entities=[],
                query=user_input,
                context=context,
            )

    def _parse_intent_json(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中解析 JSON。"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法解析意图 JSON: {text[:200]}")
        return {}

    def _build_response_prompt(
        self,
        user_input: str,
        cognitive_context: Dict[str, Any],
        prompt_config: PromptConfig,
        tool_result: Optional[ToolResult] = None,
    ) -> str:
        """构建回复生成的用户 prompt。
        
        Args:
            user_input: 用户输入
            cognitive_context: 认知上下文（画像、记忆、RAG）
            prompt_config: Prompt 配置
            tool_result: 工具执行结果（如果有）
        """
        
        # 构建各个上下文段落
        profile_section = ""
        if cognitive_context.get("user_profile"):
            profile = cognitive_context["user_profile"]
            if isinstance(profile, dict):
                profile_section = f"【用户画像】\n{json.dumps(profile, ensure_ascii=False, indent=2)}"
            else:
                profile_section = f"【用户画像】\n{profile}"

        memory_section = ""
        working_memory = cognitive_context.get("working_memory") or []
        if working_memory:
            recent_msgs = []
            for m in working_memory[-5:]:  # 最近 5 条
                role = m.get("role", "?")
                content = m.get("content", "")[:200]
                recent_msgs.append(f"  - {role}: {content}")
            memory_section = "【最近对话】\n" + "\n".join(recent_msgs)

        rag_section = ""
        rag_memories = cognitive_context.get("rag_memories") or []
        if rag_memories:
            rag_items = []
            for r in rag_memories[:3]:  # top 3
                content = r.get("content", "")[:300]
                score = r.get("score", 0)
                rag_items.append(f"  - [相关度:{score:.2f}] {content}")
            rag_section = "【相关记忆】\n" + "\n".join(rag_items)

        # 构建工具结果段落
        tool_section = ""
        if tool_result:
            tool_section = self._format_tool_result(tool_result)

        # 用模板填充
        base_prompt = prompt_config.response_user_template.format(
            input=user_input,
            profile_section=profile_section,
            memory_section=memory_section,
            rag_section=rag_section,
        )
        
        # 如果有工具结果，添加到 prompt 中
        if tool_section:
            base_prompt = f"{tool_section}\n\n{base_prompt}"
        
        return base_prompt

    def _format_tool_result(self, tool_result: ToolResult) -> str:
        """格式化工具结果，用于加入回复 prompt。"""
        if not tool_result.success:
            return f"【工具调用失败】\n工具: {tool_result.tool_name}\n错误: {tool_result.error}"
        
        result = tool_result.result
        
        # 如果是八字排盘结果，使用 summary
        if isinstance(result, dict):
            if "summary" in result:
                return f"【工具结果 - {tool_result.tool_name}】\n{result['summary']}"
            else:
                # 其他工具，格式化为 JSON
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                # 限制长度
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "\n... (结果已截断)"
                return f"【工具结果 - {tool_result.tool_name}】\n{result_str}"
        
        return f"【工具结果 - {tool_result.tool_name}】\n{str(result)}"

    async def process_request(self, request: CognitiveRequest) -> CognitiveResponse:
        """主认知处理流程。"""
        start_time = datetime.now()
        session_id = request.session_id or str(uuid.uuid4())

        logger.info(f"开始处理认知请求: session_id={session_id}")

        # 获取本次请求的 prompt 配置
        prompt_config = self._get_prompt_config(request)

        # 1. 意图理解（使用 LLM）
        intent = await self._understand_intent(
            user_input=request.input,
            context=request.context,
            prompt_config=prompt_config,
        )
        logger.info(f"意图分析完成: category={intent.category}, confidence={intent.confidence}, needs_tool={intent.needs_tool}")

        # 1.5 根据意图类别切换行业 Prompt（如果请求没有覆盖）
        if not request.response_system_prompt:
            # 根据 category 获取行业 Prompt
            industry_prompt = get_prompt_for_context(
                project_id=request.project_id,
                industry=intent.category,
            )
            prompt_config = prompt_config.override(
                response_system=industry_prompt.response_system_prompt,
            )
            logger.debug(f"已切换到行业 Prompt: {intent.category}")

        # 2. 工具调用（如果需要）
        tool_result: Optional[ToolResult] = None
        if intent.needs_tool:
            tool_result = await self.tool_orchestrator.process(
                user_input=request.input,
                intent=intent,
                user_id=request.user_id,
                project_id=request.project_id,
                session_id=session_id,
            )
            if tool_result:
                logger.info(f"工具调用完成: {tool_result.tool_name}, success={tool_result.success}")

        # 3. 获取上下文（通过 memRag）
        cognitive_context = await self.context_aggregator.get_cognitive_context(
            query=intent.query,
            user_id=request.user_id,
            session_id=session_id,
            project_id=request.project_id,
            context_config={
                "memory_depth": request.memory_depth,
                "knowledge_limit": request.rag_level * 2 if request.rag_level > 0 else 0,
                "enable_profile": True,
            },
        )

        # 4. 构建回复 prompt 并调用 LLM
        user_prompt = self._build_response_prompt(
            user_input=request.input,
            cognitive_context=cognitive_context,
            prompt_config=prompt_config,
            tool_result=tool_result,  # 传入工具结果
        )

        messages = [
            {"role": "system", "content": prompt_config.response_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        ai_text = await self.response_client.generate(messages, temperature=0.5)

        processing_time = (datetime.now() - start_time).total_seconds()

        response = CognitiveResponse(
            content=ai_text,
            intent=intent,
            confidence=intent.confidence,
            processing_time=processing_time,
            ai_service_used="daoyou-ai-service",
            tokens_used=0,
            session_id=session_id,
            user_id=request.user_id,
            tool_used=tool_result.tool_name if tool_result else None,
        )

        # 5. 学习闭环
        if request.enable_learning:
            try:
                await self._learn_from_interaction(request, response.content, session_id)
            except Exception as exc:
                logger.error(f"交互学习失败: {exc}")

        # 6. 自反省（已集成到 memory profile 聚合流程，此处不单独调用）
        # 反省逻辑由 memRag 的 profile_job 统一处理，避免额外 LLM 调用

        logger.info(
            f"认知处理完成: session_id={session_id}, 耗时={processing_time:.2f}秒, tool={response.tool_used}"
        )
        return response

    async def process_request_stream(self, request: CognitiveRequest):
        """流式处理认知请求（SSE）
        
        与 process_request 流程相同，但回复生成部分使用流式输出。
        
        SSE 事件格式:
        - event: intent     -> 意图分析结果
        - event: tool       -> 工具调用结果（如果有）
        - event: content    -> 回复内容片段
        - event: done       -> 完成信号
        - event: error      -> 错误信息
        """
        start_time = datetime.now()
        session_id = request.session_id or str(uuid.uuid4())
        
        try:
            # 1. 意图理解
            prompt_config = self._get_prompt_config(request)
            intent = await self._understand_intent(request.input, request.context, prompt_config)
            
            # 发送意图事件
            intent_data = {
                "category": intent.category,
                "confidence": intent.confidence,
                "summary": intent.summary,
                "needs_tool": intent.needs_tool,
            }
            yield f"event: intent\ndata: {json.dumps(intent_data, ensure_ascii=False)}\n\n"
            
            # 2. 工具调用（如果需要）
            tool_result = None
            if request.enable_tools and intent.needs_tool:
                tool_result = await self.tool_orchestrator.process(
                    user_input=request.input,
                    intent=intent,
                    user_id=request.user_id,
                    project_id=request.project_id,
                )
                if tool_result:
                    tool_data = {
                        "tool_name": tool_result.tool_name,
                        "success": tool_result.success,
                        "has_result": tool_result.result is not None,
                    }
                    yield f"event: tool\ndata: {json.dumps(tool_data, ensure_ascii=False)}\n\n"
            
            # 3. 上下文聚合
            cognitive_context = await self.context_aggregator.get_cognitive_context(
                query=request.input,
                user_id=request.user_id,
                session_id=session_id,
                project_id=request.project_id,
                context_config={
                    "memory_depth": request.memory_depth,
                    "knowledge_limit": request.rag_level * 2 if request.rag_level > 0 else 0,
                    "enable_profile": True,
                },
            )
            
            # 4. 构建回复 prompt
            user_prompt = self._build_response_prompt(
                user_input=request.input,
                cognitive_context=cognitive_context,
                prompt_config=prompt_config,
                tool_result=tool_result,
            )
            
            messages = [
                {"role": "system", "content": prompt_config.response_system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            # 5. 流式生成回复
            full_content = ""
            async for chunk in self.response_client.generate_stream(messages, temperature=0.5):
                full_content += chunk
                yield f"event: content\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            
            # 6. 学习闭环（异步，不阻塞）
            if request.enable_learning and full_content:
                try:
                    await self._learn_from_interaction(request, full_content, session_id)
                except Exception as exc:
                    logger.error(f"交互学习失败: {exc}")
            
            # 7. 发送完成事件
            processing_time = (datetime.now() - start_time).total_seconds()
            done_data = {
                "session_id": session_id,
                "processing_time": processing_time,
                "tool_used": tool_result.tool_name if tool_result else None,
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            
            logger.info(f"流式处理完成: session_id={session_id}, 耗时={processing_time:.2f}秒")
            
        except Exception as exc:
            logger.error(f"流式处理失败: {exc}")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    async def _learn_from_interaction(
        self,
        request: CognitiveRequest,
        response_text: str,
        session_id: str,
    ) -> None:
        """精简版交互学习逻辑，基于 memRag 的 Memory REST API。

        当前实现：
        - 将本轮对话写入一条 episodic 记忆；
        - 调用 profile auto job，根据 semantic 增量决定是否聚合用户画像。
        """

        if not request.user_id:
            return

        memory_client = get_memory_client()

        # 1) 存一条情节记忆，记录本轮问答内容
        episodic_content = f"用户询问: {request.input}\n系统回复: {response_text}"

        metadata: Dict[str, Any] = {
            "query": request.input,
            "response": response_text,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await memory_client.create_memory(
                text=episodic_content,
                user_id=request.user_id,
                project_id=getattr(request, "project_id", None),
                mem_type="episodic",
                source="daoyou_interaction",
                importance=0.6,
                tags=["interaction", "dialogue"],
                metadata=metadata,
            )
        except Exception as exc:
            logger.error(f"存储情节记忆失败: {exc}")

        # 2) 触发画像聚合的自动 Job（内部会根据 semantic 增量判断是否需要新建）
        try:
            await memory_client.create_profile_job_auto(
                user_id=request.user_id,
                project_id=getattr(request, "project_id", None),
                session_id=session_id,
            )
        except Exception as exc:
            logger.error(f"创建画像聚合任务失败: {exc}")


_cognitive_controller_instance: Optional[CognitiveController] = None


def get_cognitive_controller() -> CognitiveController:
    global _cognitive_controller_instance
    if _cognitive_controller_instance is None:
        _cognitive_controller_instance = CognitiveController()
    return _cognitive_controller_instance


def reset_cognitive_controller() -> None:
    global _cognitive_controller_instance
    _cognitive_controller_instance = None
