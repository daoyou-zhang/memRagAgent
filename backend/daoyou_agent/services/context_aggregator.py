"""道友认知服务 - 上下文聚合器

职责：
- 从 memRag 获取完整的认知上下文
- 整合用户画像、工作记忆、RAG 检索结果
- 为 LLM 回复生成提供丰富的上下文信息

工作流程：
1. 接收查询和用户信息
2. 调用 memRag 的 /api/memory/context/full 接口
3. 返回整合后的上下文（profile + working_memory + rag_memories）

依赖：
- MemoryClient: 负责与 memRag 服务通信
"""
from typing import Any, Dict, Optional

from loguru import logger

from ..services.memory_client import get_memory_client


class ContextAggregator:
    """上下文聚合器
    
    将 memRag 返回的原始数据整理成认知控制器需要的格式。
    后续可扩展：加入知识库检索、MCP 工具上下文等。
    """

    def __init__(self) -> None:
        """初始化上下文聚合器"""
        self._memory_client = get_memory_client()
        logger.info("上下文聚合器初始化完成（基于 memRag）")

    async def get_cognitive_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
        context_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """获取认知上下文
        
        Args:
            query: 用户查询内容
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            context_config: 上下文配置
                - memory_depth: 获取最近多少条对话
                - knowledge_limit: RAG 检索返回多少条
                - enable_profile: 是否获取用户画像
                
        Returns:
            上下文字典，包含:
            - user_profile: 用户画像
            - working_memory: 最近对话记录
            - rag_memories: RAG 检索到的相关记忆
            - debug_info: 调试信息
        """
        config = context_config or {}
        memory_depth = config.get("memory_depth")
        knowledge_limit = config.get("knowledge_limit")

        # memRag 的 /context/full 接口要求 project_id 和 session_id 必须有值
        # 如果缺失，返回空上下文（优雅降级）
        if not project_id or not session_id:
            logger.warning(
                f"跳过 memRag 上下文调用: project_id={project_id}, session_id={session_id}"
            )
            return {
                "user_profile": None,
                "working_memory": [],
                "rag_memories": [],
                "debug_info": {"source": "skipped_missing_params"},
            }

        try:
            # 调用 memRag 获取完整上下文
            raw = await self._memory_client.get_full_context(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                query=query,
                recent_message_limit=memory_depth,
                rag_top_k=knowledge_limit,
            )

            # 添加调试信息
            debug_info = raw.get("debug_info", {})
            debug_info.setdefault("source", "memRag/context/full")
            raw["debug_info"] = debug_info
            
            return raw
            
        except Exception as exc:
            logger.error(f"获取上下文失败: {exc}")
            return {
                "error": str(exc),
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
            }


_context_aggregator_instance: Optional[ContextAggregator] = None


def get_context_aggregator() -> ContextAggregator:
    global _context_aggregator_instance
    if _context_aggregator_instance is None:
        _context_aggregator_instance = ContextAggregator()
    return _context_aggregator_instance


def reset_context_aggregator() -> None:
    global _context_aggregator_instance
    _context_aggregator_instance = None
