"""认知大脑客户端

调用 daoyou_agent 的认知服务
"""
import os
from typing import Optional, Dict, Any, AsyncIterator
import httpx
from loguru import logger


class BrainClient:
    """认知大脑客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("BRAIN_BASE", "http://localhost:8000")).rstrip("/")
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        logger.info(f"认知大脑客户端初始化: {self.base_url}")
    
    async def process(
        self,
        user_input: str,
        user_id: str,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ):
        """处理认知请求
        
        Args:
            user_input: 用户输入
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            stream: 是否流式响应
            **kwargs: 其他参数（memory_depth, rag_level 等）
        """
        url = f"{self.base_url}/api/v1/cognitive/process"
        
        payload = {
            "input": user_input,
            "user_id": user_id,
            "session_id": session_id,
            "project_id": project_id or os.getenv("MEMRAG_PROJECT_ID", "DAOYOUTEST"),
            "stream": stream,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    # 流式响应
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                yield line[6:]  # 去掉 "data: " 前缀
                else:
                    # 普通响应
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    yield response.json()
        except httpx.HTTPError as exc:
            logger.error(f"认知大脑请求失败: {exc}")
            raise
    
    async def process_stream(
        self,
        user_input: str,
        user_id: str,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式处理认知请求"""
        async for chunk in self.process(
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            stream=True,
            **kwargs
        ):
            yield chunk


# 单例
_brain_client: Optional[BrainClient] = None


def get_brain_client() -> BrainClient:
    """获取认知大脑客户端单例"""
    global _brain_client
    if _brain_client is None:
        _brain_client = BrainClient()
    return _brain_client


# 单例
_brain_client: Optional[BrainClient] = None


def get_brain_client() -> BrainClient:
    """获取认知大脑客户端单例"""
    global _brain_client
    if _brain_client is None:
        _brain_client = BrainClient()
    return _brain_client
