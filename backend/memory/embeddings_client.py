import os
import hashlib
import sys
from typing import List
from pathlib import Path

import requests
from dotenv import load_dotenv

# 确保 .env 被加载（与 db_session / llm_client 中的 load_dotenv 幂等）
load_dotenv()

# 添加 shared 模块路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

EMBEDDINGS_BASE = os.getenv("API_EMBEDDINGS_BASE", "").rstrip("/")
EMBEDDINGS_NAME = os.getenv("EMBEDDINGS_NAME", "")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "")  # 目前仅做记录
API_EMBEDDINGS_KEY = os.getenv("API_EMBEDDINGS_KEY", "")


def _build_url(path: str) -> str:
    if not EMBEDDINGS_BASE:
        raise RuntimeError("API_EMBEDDINGS_BASE not configured in environment")
    return f"{EMBEDDINGS_BASE}{path}"


def _text_hash(text: str) -> str:
    """生成文本哈希用于缓存键"""
    return hashlib.md5(text.encode()).hexdigest()


def generate_embedding(text: str, use_cache: bool = True) -> List[float]:
    """调用向量模型生成单条文本的 embedding。

    当前假设后端 API 与 OpenAI 风格兼容：POST /embeddings
    请求体形如：{"model": ..., "input": text}
    响应体中 embeddings 位于 data[0].embedding。
    
    Args:
        text: 输入文本
        use_cache: 是否使用缓存（默认 True）
    """

    if not EMBEDDINGS_NAME:
        raise RuntimeError("EMBEDDINGS_NAME not configured in environment")
    if not API_EMBEDDINGS_KEY:
        raise RuntimeError("API_EMBEDDINGS_KEY not configured in environment")

    # 尝试从缓存获取
    text_hash = _text_hash(text)
    if use_cache:
        try:
            from shared.cache import get_cache_service
            cache = get_cache_service()
            cached = cache.get_embedding(text_hash)
            if cached:
                return cached
        except Exception:
            pass  # 缓存失败不影响主流程

    url = _build_url("/embeddings")
    payload = {
        "model": EMBEDDINGS_NAME,
        "input": text,
    }
    headers = {
        "Authorization": f"Bearer {API_EMBEDDINGS_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"Embeddings API error: {resp.status_code} {resp.text}")

    data = resp.json()
    # 兼容 OpenAI 风格：data[0].embedding
    items = data.get("data") or []
    if not items:
        raise RuntimeError("Embeddings API returned no data")
    emb = items[0].get("embedding")
    if not isinstance(emb, list):
        raise RuntimeError("Embeddings API returned invalid embedding format")
    
    # 转换为 float 列表
    result = [float(x) for x in emb]
    
    # 写入缓存
    if use_cache:
        try:
            from shared.cache import get_cache_service
            cache = get_cache_service()
            cache.set_embedding(text_hash, result)
        except Exception:
            pass
    
    return result
