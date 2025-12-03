import os
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv


# 确保 .env 被加载（与 db_session 中的 load_dotenv 是幂等的，多次调用无害）
load_dotenv()

API_BASE = os.getenv("API_MODEL_BASE", "").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")  # 目前仅做记录，不影响调用
API_MODEL_KEYS = os.getenv("API_MODEL_KEYS", "")
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "600"))
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.5"))


def _get_api_key() -> str:
    # 简单策略：从逗号分隔的 key 列表中取第一个非空 key
    if not API_MODEL_KEYS:
        raise RuntimeError("API_MODEL_KEYS not configured in environment")
    for k in API_MODEL_KEYS.split(","):
        k = k.strip()
        if k:
            return k
    raise RuntimeError("No valid API key found in API_MODEL_KEYS")


def _build_url(path: str) -> str:
    if not API_BASE:
        raise RuntimeError("API_MODEL_BASE not configured in environment")
    return f"{API_BASE}{path}"


def chat_completion(messages: List[Dict[str, Any]], max_tokens: int | None = None) -> str:
    """调用兼容 OpenAI 的 /chat/completions 接口，返回单条回答文本。

    这里只做非常薄的一层封装，便于在 routes 中专注业务逻辑。
    """

    if not MODEL_NAME:
        raise RuntimeError("MODEL_NAME not configured in environment")

    url = _build_url("/chat/completions")
    api_key = _get_api_key()

    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": MODEL_TEMPERATURE,
    }
    if max_tokens is not None:
        payload["max_tokens"] = min(max_tokens, MODEL_MAX_TOKENS)
    else:
        payload["max_tokens"] = MODEL_MAX_TOKENS

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"LLM API error: {resp.status_code} {resp.text}")

    data = resp.json()
    # 兼容 OpenAI 风格返回：choices[0].message.content
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM API returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("LLM API returned empty content")
    return content.strip()


def generate_episodic_summary(
    session_id: str,
    start_message_id: int | None,
    end_message_id: int | None,
) -> str:
    """为一次会话生成情节总结（episodic summary）。

    MVP 版本：
    - 先不从 conversation_messages 表中读取具体内容，只根据 meta 信息让大模型输出一条简要总结；
    - 后续可以在这里接入真实的对话内容，提升总结质量。
    """

    system_prompt = (
        "你是一个记忆管理助手，只负责根据给出的元信息，"
        "用简短的中文描述一次会话/任务的大致内容。"
        "回答应当简洁，1~3 句话，偏向总结‘这次主要做了什么’。"
    )

    user_prompt = (
        "现在有一条会话需要生成情节总结 (episodic summary)。\n"
        f"- 会话 ID: {session_id}\n"
        f"- 消息 ID 范围: {start_message_id} ~ {end_message_id}\n\n"
        "目前系统尚未提供具体的对话内容，请你输出一条合理的、占位性的总结文案，"
        "描述这次会话大致是在进行某种配置、设计或讨论。不要编造过多细节，"
        "用自然、通顺的中文总结一两句即可。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return chat_completion(messages)
