import os
from typing import List

import requests
from dotenv import load_dotenv

# 确保 .env 被加载（与 db_session / llm_client 中的 load_dotenv 幂等）
load_dotenv()

EMBEDDINGS_BASE = os.getenv("API_EMBEDDINGS_BASE", "").rstrip("/")
EMBEDDINGS_NAME = os.getenv("EMBEDDINGS_NAME", "")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "")  # 目前仅做记录
API_EMBEDDINGS_KEY = os.getenv("API_EMBEDDINGS_KEY", "")


def _build_url(path: str) -> str:
    if not EMBEDDINGS_BASE:
        raise RuntimeError("API_EMBEDDINGS_BASE not configured in environment")
    return f"{EMBEDDINGS_BASE}{path}"


def generate_embedding(text: str) -> List[float]:
    """调用向量模型生成单条文本的 embedding。

    当前假设后端 API 与 OpenAI 风格兼容：POST /embeddings
    请求体形如：{"model": ..., "input": text}
    响应体中 embeddings 位于 data[0].embedding。
    """

    if not EMBEDDINGS_NAME:
        raise RuntimeError("EMBEDDINGS_NAME not configured in environment")
    if not API_EMBEDDINGS_KEY:
        raise RuntimeError("API_EMBEDDINGS_KEY not configured in environment")

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
    # 简单保证都是 float
    return [float(x) for x in emb]
