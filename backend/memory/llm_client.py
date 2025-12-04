import os
from typing import List, Dict, Any
import json

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
    conversation_text: str,
) -> str:
    """为一次会话生成情节总结（episodic summary）。

    输入为会话 ID 以及整理好的对话文本（可只包含截取后的若干条消息）。
    """

    # 为避免超长对话影响效果和消耗，简单截断到前后若干字符
    if len(conversation_text) > 4000:
        conversation_text = conversation_text[-4000:]

    system_prompt = (
        "你是一个记忆管理助手，负责根据对话内容生成情节总结 (episodic memory)。"
        "请用简洁的中文总结这次会话/任务："
        "1) 主要在讨论或实现什么；2) 做出了哪些关键决策或设计结论；"
        "3) 可以适当提及重要的模块/表/字段等关键词，方便后续检索。"
        "回答控制在 2~6 句话，不要复述所有细节。"
    )

    user_prompt = (
        "下面是一段会话内容，请基于这些内容生成一条情节总结 (episodic summary)。\n"
        f"- 会话 ID: {session_id}\n\n"
        "【对话内容摘录】\n"
        f"{conversation_text}\n\n"
        "请按照系统提示生成总结。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return chat_completion(messages)


def generate_semantic_memories(
    session_id: str,
    conversation_text: str,
) -> List[Dict[str, Any]]:
    """从一段对话内容中抽取若干条 semantic 记忆。

    返回值为若干条结构化条目，每条包含至少 text 字段，可选 category / tags。
    具体落库由调用方决定。
    """

    if len(conversation_text) > 4000:
        conversation_text = conversation_text[-4000:]

    system_prompt = (
        "你是一个用户画像和长期记忆抽取助手，负责从对话中提取可以长期保存的事实和偏好 "
        "(semantic memory)。这些信息将用于后续的人格画像和检索。\n\n"
        "请优先关注以下几个维度：\n"
        "- 沟通与表达偏好（语言、回答风格、细节程度、展示形式等）；\n"
        "- 知识与兴趣领域（工作/专业领域、长期关注的话题、兴趣爱好等）；\n"
        "- 决策与风险偏好（保守/激进、是否喜欢多方案选择等）；\n"
        "- 交互风格（是否喜欢系统提问澄清、是否接受直接指出问题等）；\n"
        "- 常用工具或工作/学习方式（如果对话中有体现）。\n\n"
        "输出时请使用 JSON 数组格式，每个元素是一个对象，形如：\n"
        "{\"text\": \"一句话结论\", \"category\": \"communication\", \"tags\": [\"preference\", \"communication\"]}。\n"
        "如果对话信息不足，可以返回空数组 []。不要编造与对话无关的内容。"
    )

    user_prompt = (
        "下面是一段会话内容，请基于这些内容提取 0~若干条适合长期保存的 semantic 记忆：\n"
        f"- 会话 ID: {session_id}\n\n"
        "【对话内容摘录】\n"
        f"{conversation_text}\n\n"
        "请只输出一个 JSON 数组，不要包含其他解释性文字。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = chat_completion(messages)

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            # 只保留 dict 条目
            return [x for x in data if isinstance(x, dict)]
        return []
    except json.JSONDecodeError:
        # 如果解析失败，直接忽略本次抽取
        return []
