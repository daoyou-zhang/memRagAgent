"""道友认知服务 - 记忆客户端

职责：
- 与 memRag 记忆服务进行 HTTP 通信
- 提供异步 API 封装，简化调用

功能：
- get_full_context(): 获取完整认知上下文（画像+对话+RAG）
- create_memory(): 创建记忆（情节/语义/程序等）
- create_profile_job_auto(): 触发用户画像自动聚合

配置：
- 环境变量 MEMORY_SERVICE_BASE_URL: memRag 服务地址，默认 http://127.0.0.1:5000
"""
import os
from typing import Any, Dict, Optional, List

import httpx


class MemoryClient:
    """记忆服务客户端
    
    负责与 memRag（记忆微服务）通信。
    所有方法都是异步的，使用 httpx.AsyncClient。
    """

    def __init__(self) -> None:
        """初始化客户端，读取 memRag 服务地址"""
        base = os.getenv("MEMORY_SERVICE_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
        self.base_url = base

    async def get_full_context(
        self,
        user_id: Optional[str],
        project_id: Optional[str],
        session_id: Optional[str],
        query: Optional[str] = None,
        recent_message_limit: Optional[int] = None,
        rag_top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取完整认知上下文
        
        调用 memRag 的 /api/memory/context/full 接口。
        
        Args:
            user_id: 用户 ID
            project_id: 项目 ID（必填）
            session_id: 会话 ID（必填）
            query: 查询内容（用于 RAG 检索）
            recent_message_limit: 最近对话条数限制
            rag_top_k: RAG 返回条数限制
            
        Returns:
            包含 user_profile, working_memory, rag_memories 的字典
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
        }
        if query is not None:
            payload["query"] = query
        if recent_message_limit is not None:
            payload["recent_message_limit"] = recent_message_limit
        if rag_top_k is not None:
            payload["rag_top_k"] = rag_top_k

        url = f"{self.base_url}/api/memory/context/full"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        return resp.json()

    async def create_memory(
        self,
        *,
        text: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        mem_type: str = "semantic",
        source: str = "daoyou",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建记忆
        
        调用 memRag 的 /api/memory/memories 接口。
        用于学习闭环：存储每次对话的情节记忆。
        
        Args:
            text: 记忆内容
            user_id: 用户 ID
            project_id: 项目 ID
            agent_id: 智能体 ID
            mem_type: 记忆类型（semantic/episodic/procedural/working）
            source: 来源标识
            importance: 重要性（0-1）
            tags: 标签列表
            metadata: 额外元数据
            
        Returns:
            创建的记忆记录
        """

        payload: Dict[str, Any] = {
            "text": text,
            "user_id": user_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "type": mem_type,
            "source": source,
            "importance": importance,
        }
        if tags is not None:
            payload["tags"] = tags
        if metadata is not None:
            payload["metadata"] = metadata

        url = f"{self.base_url}/api/memory/memories"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        return resp.json()

    async def create_profile_job_auto(
        self,
        *,
        user_id: str,
        project_id: Optional[str] = None,
        min_new_semantic: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """触发用户画像自动聚合
        
        调用 memRag 的 /api/memory/jobs/profile/auto 接口。
        根据新增的语义记忆数量判断是否需要重新聚合用户画像。
        
        Args:
            user_id: 用户 ID（必填）
            project_id: 项目 ID
            min_new_semantic: 触发聚合的最小新语义记忆数
            session_id: 会话 ID
            
        Returns:
            Job 状态信息
        """

        payload: Dict[str, Any] = {
            "user_id": user_id,
        }
        if project_id is not None:
            payload["project_id"] = project_id
        if min_new_semantic is not None:
            payload["min_new_semantic"] = int(min_new_semantic)
        if session_id is not None:
            payload["session_id"] = session_id

        url = f"{self.base_url}/api/memory/jobs/profile/auto"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


    async def record_conversation(
        self,
        *,
        user_id: Optional[str],
        session_id: str,
        project_id: Optional[str] = None,
        raw_query: str,
        optimized_query: Optional[str] = None,
        intent: Optional[Dict[str, Any]] = None,
        tool_used: Optional[str] = None,
        tool_result: Optional[str] = None,
        context_used: Optional[Dict[str, Any]] = None,
        llm_response: str,
        processing_time: float = 0,
        auto_generate_memory: bool = True,
    ) -> Dict[str, Any]:
        """记录完整对话（统一由 memory 服务处理）
        
        调用 memRag 的 /api/conversations/record 接口。
        memory 服务负责：
        - 存储对话消息
        - 创建记忆生成 Job
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID（必填）
            project_id: 项目 ID
            raw_query: 用户原始输入
            optimized_query: RAG 优化后的查询
            intent: 意图分析结果
            tool_used: 使用的工具名称
            tool_result: 工具结果摘要
            context_used: 使用的上下文信息
            llm_response: LLM 最终回复
            processing_time: 处理耗时（秒）
            auto_generate_memory: 是否自动生成记忆
            
        Returns:
            记录结果
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "project_id": project_id,
            "raw_query": raw_query,
            "llm_response": llm_response,
            "processing_time": processing_time,
            "auto_generate_memory": auto_generate_memory,
        }
        if optimized_query:
            payload["optimized_query"] = optimized_query
        if intent:
            payload["intent"] = intent
        if tool_used:
            payload["tool_used"] = tool_used
        if tool_result:
            payload["tool_result"] = tool_result
        if context_used:
            payload["context_used"] = context_used

        url = f"{self.base_url}/api/conversations/record"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


_memory_client: Optional[MemoryClient] = None


def get_memory_client() -> MemoryClient:
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient()
    return _memory_client
