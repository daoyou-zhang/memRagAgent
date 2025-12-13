"""Redis 缓存服务

提供统一的缓存接口，用于热点数据缓存。
支持：用户画像、RAG 结果、图谱查询结果等。
"""
import os
import json
import hashlib
from typing import Optional, Any, Callable
from pathlib import Path
from functools import wraps

import redis
from dotenv import load_dotenv
from loguru import logger

# 加载配置
_backend_root = Path(__file__).parent.parent
load_dotenv(_backend_root / ".env")

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "300"))  # 默认 5 分钟

# Redis 客户端单例
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端单例"""
    global _redis_client
    
    if not REDIS_ENABLED:
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 测试连接
            _redis_client.ping()
            logger.info("[Redis] 连接成功")
        except Exception as e:
            logger.warning(f"[Redis] 连接失败: {e}")
            _redis_client = None
    
    return _redis_client


class CacheService:
    """缓存服务"""
    
    # 缓存键前缀
    PREFIX = "memrag:"
    
    # 不同数据类型的 TTL（秒）
    TTL_PROFILE = 600      # 用户画像 10 分钟
    TTL_RAG = 300          # RAG 结果 5 分钟
    TTL_GRAPH = 600        # 图谱查询 10 分钟
    TTL_EMBEDDING = 3600   # Embedding 1 小时
    TTL_SHORT = 60         # 短期缓存 1 分钟
    
    def __init__(self):
        self.client = get_redis_client()
    
    def _make_key(self, namespace: str, *args) -> str:
        """生成缓存键"""
        parts = [self.PREFIX, namespace]
        for arg in args:
            if arg is not None:
                parts.append(str(arg))
        return ":".join(parts)
    
    def _hash_key(self, data: str) -> str:
        """对长字符串生成哈希键"""
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    # ========== 基础操作 ==========
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.client:
            return None
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[Cache] get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存"""
        if not self.client:
            return False
        try:
            ttl = ttl or REDIS_CACHE_TTL
            self.client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"[Cache] set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.client:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"[Cache] delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self.client:
            return 0
        try:
            keys = self.client.keys(f"{self.PREFIX}{pattern}")
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"[Cache] delete_pattern error: {e}")
            return 0
    
    # ========== 业务缓存 ==========
    
    def get_profile(self, user_id: str, project_id: str) -> Optional[dict]:
        """获取用户画像缓存"""
        key = self._make_key("profile", user_id, project_id)
        return self.get(key)
    
    def set_profile(self, user_id: str, project_id: str, profile: dict) -> bool:
        """设置用户画像缓存"""
        key = self._make_key("profile", user_id, project_id)
        return self.set(key, profile, self.TTL_PROFILE)
    
    def invalidate_profile(self, user_id: str, project_id: str = None) -> int:
        """使用户画像缓存失效"""
        if project_id:
            key = self._make_key("profile", user_id, project_id)
            return 1 if self.delete(key) else 0
        else:
            # 删除该用户所有项目的画像缓存
            return self.delete_pattern(f"profile:{user_id}:*")
    
    def get_rag(self, query_hash: str, project_id: str, user_id: str = None) -> Optional[list]:
        """获取 RAG 结果缓存"""
        key = self._make_key("rag", project_id, user_id or "_", query_hash)
        return self.get(key)
    
    def set_rag(self, query_hash: str, project_id: str, results: list, user_id: str = None) -> bool:
        """设置 RAG 结果缓存"""
        key = self._make_key("rag", project_id, user_id or "_", query_hash)
        return self.set(key, results, self.TTL_RAG)
    
    def get_graph(self, query_hash: str) -> Optional[dict]:
        """获取图谱查询缓存"""
        key = self._make_key("graph", query_hash)
        return self.get(key)
    
    def set_graph(self, query_hash: str, result: dict) -> bool:
        """设置图谱查询缓存"""
        key = self._make_key("graph", query_hash)
        return self.set(key, result, self.TTL_GRAPH)
    
    def get_embedding(self, text_hash: str) -> Optional[list]:
        """获取 Embedding 缓存"""
        key = self._make_key("emb", text_hash)
        return self.get(key)
    
    def set_embedding(self, text_hash: str, embedding: list) -> bool:
        """设置 Embedding 缓存"""
        key = self._make_key("emb", text_hash)
        return self.set(key, embedding, self.TTL_EMBEDDING)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        if not self.client:
            return {"enabled": False}
        try:
            info = self.client.info("memory")
            keys = self.client.dbsize()
            return {
                "enabled": True,
                "keys": keys,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": self.client.info("clients").get("connected_clients", 0),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# 单例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取 CacheService 单例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ========== 装饰器 ==========

def cached(namespace: str, ttl: int = None, key_func: Callable = None):
    """缓存装饰器
    
    Args:
        namespace: 缓存命名空间
        ttl: 过期时间（秒）
        key_func: 自定义键生成函数，接收 *args, **kwargs，返回字符串
    
    Usage:
        @cached("profile", ttl=600)
        def get_user_profile(user_id, project_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_service()
            if not cache.client:
                return func(*args, **kwargs)
            
            # 生成缓存键
            if key_func:
                cache_key_suffix = key_func(*args, **kwargs)
            else:
                # 默认用参数生成键
                key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key_suffix = cache._hash_key(":".join(key_parts))
            
            cache_key = cache._make_key(namespace, cache_key_suffix)
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            if result is not None:
                cache.set(cache_key, result, ttl or REDIS_CACHE_TTL)
            
            return result
        return wrapper
    return decorator
