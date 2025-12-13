"""道友认知服务 - LLM 适配器

支持按请求配置不同模型，使用客户端池复用连接。

架构说明：
- LLMConfig: 模型配置（api_base, model_name, temperature 等）
- LLMClient: 单个 LLM 客户端，负责调用 API
- LLMClientPool: 客户端池，按配置指纹复用客户端

使用方式：
- get_intent_client(): 获取意图分析客户端（低温度、少 token）
- get_response_client(): 获取回复生成客户端（高温度、多 token）
- get_ai_service(config): 按自定义配置获取客户端
"""
import os
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from loguru import logger
from dotenv import load_dotenv

# 加载 .env 配置（从 daoyou_agent 目录）
_current_dir = Path(__file__).parent.parent  # daoyou_agent 目录
_env_path = _current_dir / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    logger.info(f"已加载配置: {_env_path}")
else:
    load_dotenv()  # 回退到默认

# ============================================================
# 默认配置（从环境变量读取，用于回复生成）
# ============================================================
DEFAULT_API_BASE = os.getenv("API_MODEL_BASE", "").rstrip("/")
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "")
DEFAULT_API_KEYS = os.getenv("API_MODEL_KEYS", "")
DEFAULT_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "6000"))
DEFAULT_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.5"))

# ============================================================
# 意图模型配置（可选，不配则回退到默认配置）
# 建议使用更快、更便宜的模型，如 qwen-flash
# ============================================================
INTENT_API_BASE = os.getenv("INTENT_API_BASE", "").rstrip("/") or DEFAULT_API_BASE
INTENT_MODEL_NAME = os.getenv("INTENT_MODEL_NAME", "") or DEFAULT_MODEL_NAME
INTENT_API_KEYS = os.getenv("INTENT_API_KEYS", "") or DEFAULT_API_KEYS
INTENT_MAX_TOKENS = int(os.getenv("INTENT_MAX_TOKENS", "2000"))
INTENT_TEMPERATURE = float(os.getenv("INTENT_TEMPERATURE", "0.1"))


@dataclass
class LLMConfig:
    """LLM 配置数据类
    
    属性:
        api_base: API 基础地址（如 https://dashscope.aliyuncs.com/compatible-mode/v1）
        model_name: 模型名称（如 deepseek-v3.2-exp, qwen-flash）
        api_keys: API 密钥，多个用逗号分隔
        max_tokens: 最大生成 token 数
        temperature: 温度参数（0-1，越低越稳定）
        timeout: 请求超时时间（秒）
    """
    api_base: str = ""
    model_name: str = ""
    api_keys: str = ""
    max_tokens: int = 6000
    temperature: float = 0.5
    timeout: float = 60.0

    def fingerprint(self) -> str:
        """生成配置指纹
        
        用于客户端池判断是否复用已有客户端。
        相同指纹的配置会复用同一个客户端。
        """
        key = f"{self.api_base}|{self.model_name}|{self.max_tokens}|{self.timeout}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def get_api_key(self) -> str:
        """获取 API 密钥
        
        从逗号分隔的 key 列表中取第一个非空 key。
        后续可扩展为轮询或负载均衡。
        """
        if not self.api_keys:
            raise RuntimeError("API 密钥未配置，请检查 .env 文件")
        for k in self.api_keys.split(","):
            k = k.strip()
            if k:
                return k
        raise RuntimeError("未找到有效的 API 密钥")

    @classmethod
    def default(cls) -> "LLMConfig":
        """获取默认配置（用于回复生成）
        
        从环境变量 MODEL_* 读取配置。
        """
        return cls(
            api_base=DEFAULT_API_BASE,
            model_name=DEFAULT_MODEL_NAME,
            api_keys=DEFAULT_API_KEYS,
            max_tokens=DEFAULT_MAX_TOKENS,
            temperature=DEFAULT_TEMPERATURE,
        )

    @classmethod
    def for_intent(cls) -> "LLMConfig":
        """获取意图分析配置
        
        从环境变量 INTENT_* 读取配置。
        特点：低温度（0.1）保证稳定输出 JSON，少 token（2000）节省成本。
        """
        return cls(
            api_base=INTENT_API_BASE,
            model_name=INTENT_MODEL_NAME,
            api_keys=INTENT_API_KEYS,
            max_tokens=INTENT_MAX_TOKENS,
            temperature=INTENT_TEMPERATURE,
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LLMConfig":
        """从字典创建配置
        
        用于支持请求级别的配置覆盖。
        未指定的字段会回退到默认配置。
        """
        base = cls.default()
        return cls(
            api_base=d.get("api_base") or base.api_base,
            model_name=d.get("model_name") or base.model_name,
            api_keys=d.get("api_keys") or base.api_keys,
            max_tokens=d.get("max_tokens") or base.max_tokens,
            temperature=d.get("temperature", base.temperature),
            timeout=d.get("timeout", base.timeout),
        )


class LLMClient:
    """LLM 客户端
    
    负责调用 OpenAI 兼容的 /chat/completions 接口。
    支持 DashScope（通义千问）、DeepSeek 等 OpenAI 兼容 API。
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化客户端
        
        Args:
            config: LLM 配置
        """
        self.config = config
        self._http_client: Optional[httpx.AsyncClient] = None

    def _is_valid(self) -> bool:
        """检查配置是否完整"""
        return bool(self.config.api_base and self.config.model_name)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """生成回复
        
        Args:
            messages: 消息列表，格式 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数，不传则使用配置默认值
            max_tokens: 最大 token 数，不传则使用配置默认值
            
        Returns:
            生成的文本内容
        """
        if not self._is_valid():
            last = messages[-1]["content"] if messages else ""
            return f"[LLM 未配置] 你说的是：{last[:200]}"

        url = f"{self.config.api_base}/chat/completions"
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens or self.config.max_tokens

        payload: Dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.config.get_api_key()}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, json=payload, headers=headers, timeout=self.config.timeout
                )

            if resp.status_code >= 400:
                logger.error(f"LLM API error: {resp.status_code} {resp.text}")
                return f"LLM 调用失败: {resp.status_code}"

            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return "LLM 返回空结果"

            content = choices[0].get("message", {}).get("content", "")
            return content.strip() if content else "LLM 返回空内容"

        except Exception as exc:
            logger.error(f"LLM request failed: {exc}")
            return f"LLM 请求异常: {exc}"

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """流式生成回复（SSE）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Yields:
            str: 流式返回的文本片段
        """
        if not self._is_valid():
            last = messages[-1]["content"] if messages else ""
            yield f"[LLM 未配置] 你说的是：{last[:200]}"
            return

        url = f"{self.config.api_base}/chat/completions"
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens or self.config.max_tokens

        payload: Dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
            "stream": True,  # 启用流式
        }

        headers = {
            "Authorization": f"Bearer {self.config.get_api_key()}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers, timeout=self.config.timeout
                ) as resp:
                    if resp.status_code >= 400:
                        error_text = await resp.aread()
                        logger.error(f"LLM API error: {resp.status_code} {error_text}")
                        yield f"LLM 调用失败: {resp.status_code}"
                        return

                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                continue
        except Exception as exc:
            logger.error(f"LLM stream request failed: {exc}")
            yield f"LLM 流式请求异常: {exc}"


class LLMClientPool:
    """LLM 客户端池
    
    按配置指纹复用客户端，避免重复创建。
    同一配置的请求会复用同一个客户端实例。
    """

    def __init__(self) -> None:
        self._clients: Dict[str, LLMClient] = {}  # 自定义配置的客户端缓存
        self._default_client: Optional[LLMClient] = None  # 默认回复客户端
        self._intent_client: Optional[LLMClient] = None   # 意图分析客户端

    def get_client(self, config: Optional[LLMConfig] = None) -> LLMClient:
        """获取客户端
        
        Args:
            config: LLM 配置，不传则返回默认客户端
            
        Returns:
            LLMClient 实例（复用或新建）
        """
        if config is None:
            if self._default_client is None:
                self._default_client = LLMClient(LLMConfig.default())
                logger.info(f"创建默认 LLM 客户端: {LLMConfig.default().model_name}")
            return self._default_client

        fp = config.fingerprint()
        if fp not in self._clients:
            self._clients[fp] = LLMClient(config)
            logger.info(f"创建 LLM 客户端 [{fp}]: {config.model_name}")
        return self._clients[fp]

    def get_intent_client(self) -> LLMClient:
        """获取意图分析专用客户端
        
        使用 INTENT_* 环境变量配置，特点是低温度、少 token。
        """
        if self._intent_client is None:
            self._intent_client = LLMClient(LLMConfig.for_intent())
            logger.info(f"创建意图分析客户端: {LLMConfig.for_intent().model_name}")
        return self._intent_client

    def get_response_client(self) -> LLMClient:
        """获取回复生成专用客户端
        
        使用默认配置（MODEL_* 环境变量）。
        """
        return self.get_client(None)


# ============================================================
# 全局客户端池（单例）
# ============================================================
_client_pool: Optional[LLMClientPool] = None


def get_client_pool() -> LLMClientPool:
    """获取全局客户端池（单例模式）"""
    global _client_pool
    if _client_pool is None:
        _client_pool = LLMClientPool()
    return _client_pool


def get_ai_service(config: Optional[LLMConfig] = None) -> LLMClient:
    """获取 LLM 客户端
    
    这是通用接口，可传入自定义配置。
    不传配置则返回默认客户端。
    """
    return get_client_pool().get_client(config)


def get_intent_client() -> LLMClient:
    """获取意图分析客户端
    
    专门用于分析用户意图，使用低温度保证输出稳定的 JSON。
    """
    return get_client_pool().get_intent_client()


def get_response_client() -> LLMClient:
    """获取回复生成客户端
    
    用于生成最终回复，使用较高温度增加创造性。
    """
    return get_client_pool().get_response_client()


__all__ = [
    "LLMConfig",
    "LLMClient",
    "LLMClientPool",
    "get_client_pool",
    "get_ai_service",
    "get_intent_client",
    "get_response_client",
]
