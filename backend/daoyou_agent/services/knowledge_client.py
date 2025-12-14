"""Knowledge 服务客户端

负责与 Knowledge 服务通信，提供知识库 RAG 查询能力。

配置：
- 环境变量 KNOWLEDGE_SERVICE_URL: Knowledge 服务地址，默认 http://127.0.0.1:5001
- 环境变量 INTERNAL_API_KEY: 服务间通信 API Key（使用管理员 Key）
"""
import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


class KnowledgeClient:
    """Knowledge 服务异步客户端"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or os.getenv("KNOWLEDGE_SERVICE_URL", "http://127.0.0.1:5001")).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        # 服务间通信使用内部 API Key（管理员权限）
        self.api_key = os.getenv("INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
        logger.info(f"KnowledgeClient 初始化: {self.base_url}")
    
    def _get_headers(self, project_id: Optional[str] = None, user_api_key: Optional[str] = None) -> Dict[str, str]:
        """获取请求头（含认证信息）
        
        Args:
            project_id: 项目 ID
            user_api_key: 用户的 API Key（优先使用，保持租户隔离）
        """
        headers = {}
        # 优先使用用户的 API Key，其次使用服务内部 Key
        api_key = user_api_key or self.api_key
        if api_key:
            headers["X-API-Key"] = api_key
        if project_id:
            headers["X-Project-Id"] = project_id
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            client = await self._get_client()
            resp = await client.get("/api/knowledge/health")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Knowledge 服务健康检查失败: {e}")
            return {"status": "error", "error": str(e)}

    async def rag_query(
        self,
        query: str,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        collection_ids: Optional[List[int]] = None,
        top_k: int = 5,
        required_tags: Optional[List[str]] = None,
        preferred_tags: Optional[List[str]] = None,
        user_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """知识库 RAG 查询
        
        Args:
            query: 查询文本
            project_id: 项目 ID
            domain: 领域过滤
            collection_ids: 指定集合 ID 列表
            top_k: 返回结果数量
            required_tags: 必须匹配的标签
            preferred_tags: 优先匹配的标签
            user_api_key: 用户的 API Key（保持租户隔离）
            
        Returns:
            {
                "used_chunks": [...],
                "debug": {...}
            }
        """
        try:
            client = await self._get_client()
            
            payload: Dict[str, Any] = {
                "query": query,
                "top_k": top_k,
            }
            if project_id:
                payload["project_id"] = project_id
            if domain:
                payload["domain"] = domain
            if collection_ids:
                payload["collection_ids"] = collection_ids
            if required_tags:
                payload["required_tags"] = required_tags
            if preferred_tags:
                payload["preferred_tags"] = preferred_tags

            headers = self._get_headers(project_id, user_api_key)
            resp = await client.post("/api/knowledge/rag/query", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Knowledge RAG 查询失败 (HTTP {e.response.status_code}): {e}")
            return {"used_chunks": [], "debug": {"error": str(e)}}
        except Exception as e:
            logger.error(f"Knowledge RAG 查询失败: {e}")
            return {"used_chunks": [], "debug": {"error": str(e)}}

    async def list_collections(
        self,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        user_api_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取知识库集合列表"""
        try:
            client = await self._get_client()
            params = {}
            if project_id:
                params["project_id"] = project_id
            if domain:
                params["domain"] = domain
            
            headers = self._get_headers(project_id, user_api_key)
            resp = await client.get("/api/knowledge/collections", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except Exception as e:
            logger.error(f"获取知识库集合失败: {e}")
            return []


# 单例
_knowledge_client: Optional[KnowledgeClient] = None


def get_knowledge_client() -> KnowledgeClient:
    global _knowledge_client
    if _knowledge_client is None:
        _knowledge_client = KnowledgeClient()
    return _knowledge_client
