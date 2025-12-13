"""道友认知服务 - 上下文聚合器

职责：
- 从 memRag 获取完整的认知上下文
- 从 Knowledge 服务获取知识库 RAG 结果
- 从 Knowledge 图谱服务获取结构化知识
- 整合用户画像、工作记忆、RAG 检索结果、知识库内容、图谱上下文
- 为 LLM 回复生成提供丰富的上下文信息

工作流程：
1. 接收查询和用户信息
2. 并行调用 memRag、Knowledge 和 Graph 服务
3. 返回整合后的上下文（profile + working_memory + rag_memories + knowledge_chunks + graph_context）

依赖：
- MemoryClient: 负责与 memRag 服务通信
- KnowledgeClient: 负责与 Knowledge 服务通信
"""
import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from ..services.memory_client import get_memory_client
from ..services.knowledge_client import get_knowledge_client


class ContextAggregator:
    """上下文聚合器
    
    将 memRag 返回的原始数据整理成认知控制器需要的格式。
    后续可扩展：加入知识库检索、MCP 工具上下文等。
    """

    def __init__(self) -> None:
        """初始化上下文聚合器"""
        self._memory_client = get_memory_client()
        self._knowledge_client = get_knowledge_client()
        logger.info("上下文聚合器初始化完成（memRag + Knowledge）")

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
                - enable_knowledge: 是否查询知识库（默认 True）
                - knowledge_domain: 知识库领域过滤
                - enable_graph: 是否查询知识图谱（默认 True）
                
        Returns:
            上下文字典，包含:
            - user_profile: 用户画像
            - working_memory: 最近对话记录
            - rag_memories: RAG 检索到的相关记忆
            - knowledge_chunks: 知识库检索结果
            - graph_context: 图谱上下文
            - debug_info: 调试信息
        """
        config = context_config or {}
        memory_depth = config.get("memory_depth")
        knowledge_limit = config.get("knowledge_limit", 5)
        enable_knowledge = config.get("enable_knowledge", True)
        enable_graph = config.get("enable_graph", True)
        knowledge_domain = config.get("knowledge_domain")

        result = {
            "user_profile": None,
            "working_memory": [],
            "rag_memories": [],
            "knowledge_chunks": [],
            "graph_context": None,
            "debug_info": {},
        }

        # 并行调用 memory 和 knowledge 服务
        tasks = []
        
        # Memory 服务调用（需要 project_id 和 session_id）
        if project_id and session_id:
            tasks.append(("memory", self._fetch_memory_context(
                query=query,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                memory_depth=memory_depth,
                knowledge_limit=knowledge_limit,
            )))
        else:
            logger.warning(f"跳过 memRag: project_id={project_id}, session_id={session_id}")
        
        # Knowledge 服务调用
        if enable_knowledge and query.strip():
            tasks.append(("knowledge", self._fetch_knowledge_context(
                query=query,
                project_id=project_id,
                domain=knowledge_domain,
                top_k=knowledge_limit,
            )))
        
        # Graph 服务调用（知识图谱增强搜索）
        if enable_graph and query.strip():
            tasks.append(("graph", self._fetch_graph_context(
                query=query,
                domain=knowledge_domain,
            )))

        # 并行执行
        if tasks:
            task_names = [t[0] for t in tasks]
            task_coros = [t[1] for t in tasks]
            results = await asyncio.gather(*task_coros, return_exceptions=True)
            
            for name, res in zip(task_names, results):
                if isinstance(res, Exception):
                    logger.error(f"{name} 调用失败: {res}")
                    result["debug_info"][f"{name}_error"] = str(res)
                elif isinstance(res, dict):
                    if name == "memory":
                        result["user_profile"] = res.get("user_profile")
                        result["working_memory"] = res.get("working_memory", [])
                        result["rag_memories"] = res.get("rag_memories", [])
                        result["debug_info"]["memory"] = res.get("debug_info", {})
                    elif name == "knowledge":
                        result["knowledge_chunks"] = res.get("used_chunks", [])
                        result["debug_info"]["knowledge"] = res.get("debug", {})
                    elif name == "graph":
                        result["graph_context"] = res.get("context_text", "")
                        result["debug_info"]["graph"] = {
                            "entities": len(res.get("graph_entities", [])),
                            "relations": len(res.get("relations", [])),
                        }

        return result

    async def _fetch_memory_context(
        self,
        query: str,
        user_id: Optional[str],
        project_id: str,
        session_id: str,
        memory_depth: Optional[int],
        knowledge_limit: Optional[int],
    ) -> Dict[str, Any]:
        """获取 Memory 服务上下文"""
        return await self._memory_client.get_full_context(
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            query=query,
            recent_message_limit=memory_depth,
            rag_top_k=knowledge_limit,
        )

    async def _fetch_knowledge_context(
        self,
        query: str,
        project_id: Optional[str],
        domain: Optional[str],
        top_k: int,
    ) -> Dict[str, Any]:
        """获取 Knowledge 服务上下文"""
        return await self._knowledge_client.rag_query(
            query=query,
            project_id=project_id,
            domain=domain,
            top_k=top_k,
        )

    async def _fetch_graph_context(
        self,
        query: str,
        domain: Optional[str],
    ) -> Dict[str, Any]:
        """获取知识图谱上下文"""
        import httpx
        import os
        
        knowledge_url = os.getenv("KNOWLEDGE_SERVICE_URL", "http://127.0.0.1:5001")
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{knowledge_url}/api/knowledge/graph/enhanced_search",
                    json={
                        "query": query,
                        "domain": domain,
                        "top_k": 10,
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Graph search failed: {response.status_code}")
                    return {}
        except Exception as e:
            logger.warning(f"Graph search error: {e}")
            return {}


_context_aggregator_instance: Optional[ContextAggregator] = None


def get_context_aggregator() -> ContextAggregator:
    global _context_aggregator_instance
    if _context_aggregator_instance is None:
        _context_aggregator_instance = ContextAggregator()
    return _context_aggregator_instance


def reset_context_aggregator() -> None:
    global _context_aggregator_instance
    _context_aggregator_instance = None
