"""LLM 处理模块

提供 LLM 调用封装，用于实体抽取等任务。
"""
import os
import json
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

# 加载配置
_backend_root = Path(__file__).parent.parent.parent
load_dotenv(_backend_root / ".env")


def call_llm(
    prompt: str,
    system_prompt: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> str:
    """调用 LLM
    
    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        max_tokens: 最大 token 数
        temperature: 温度
    
    Returns:
        LLM 响应文本
    """
    import httpx
    
    # 使用意图模型（更快更便宜）
    api_keys = os.getenv("INTENT_API_KEYS", os.getenv("API_MODEL_KEYS", "")).split(",")
    api_base = os.getenv("INTENT_API_BASE", os.getenv("API_MODEL_BASE", ""))
    model_name = os.getenv("INTENT_MODEL_NAME", os.getenv("MODEL_NAME", ""))
    
    if not api_keys or not api_keys[0]:
        raise RuntimeError("No API keys configured")
    
    api_key = api_keys[0].strip()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        
        return data["choices"][0]["message"]["content"]


def extract_json_from_response(response: str) -> Optional[list | dict]:
    """从 LLM 响应中提取 JSON
    
    处理 ```json ... ``` 包裹的情况
    """
    text = response.strip()
    
    # 移除 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 移除首行 ```json 或 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 移除末行 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 [ 或 { 开始的位置
        for i, c in enumerate(text):
            if c in "[{":
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    continue
        return None
