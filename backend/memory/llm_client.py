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

# Prompt 自进化开关（有风险，默认关闭）
PROMPT_EVOLUTION_ENABLED = os.getenv("PROMPT_EVOLUTION_ENABLED", "false").lower() in {"1", "true", "yes"}
# 统一记忆生成开关（合并 episodic + semantic + prompt suggestions 为一次 LLM 调用）
UNIFIED_MEMORY_GENERATION = os.getenv("UNIFIED_MEMORY_GENERATION", "true").lower() in {"1", "true", "yes"}


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
        "(semantic memory)。这些信息将用于后续的亲密画像和检索。\n\n"
        "请优先围绕以下六个维度提取 *结论型的一句话*：\n"
        "1) 身份与背景 identity_profile：职业/角色、技术背景、年龄段、常驻城市/时区等；\n"
        "2) 情感状态与关系 emotional_state_and_relations：长期情绪趋势、在分歧中的处理方式、与重要协作对象的大致关系模式；\n"
        "3) 交流与陪伴偏好 communication_and_companionship：语言偏好、回答风格（是否先给结论）、能接受的批判强度、希望助手更像工具/朋友/教练等；\n"
        "4) 生活习惯与兴趣 lifestyle_and_habits：作息、日常习惯、兴趣爱好（例如对量子物理特别感兴趣）、在生活决策中是否偏理性；\n"
        "5) 工作与学习风格 work_and_learning_style：是否理性批判、是否偏实用主义、合作风格（愿意讨论但最终要可执行）、学习方式（先原理/先例子等）；\n"
        "6) 边界与价值观 boundaries_and_values：不希望讨论的领域、对诚实/现实提醒的期待、在效率 vs 稳健之间的大致取向。\n\n"
        "输出时请使用 JSON 数组格式，每个元素是一个对象，形如：\n"
        "{\"text\": \"一句话结论\", \"category\": \"communication_and_companionship\", \"tags\": [\"profile:comm_style\", \"preference\"]}。\n"
        "- text：一句话结论，尽量具体且可直接用于后续推理；\n"
        "- category：上述六个维度之一的标识（如 identity_profile / lifestyle_and_habits 等）；\n"
        "- tags：包含至少一个 profile:* 或 interest:* 等标签，用于后续聚合（例如 profile:interest, interest:physics:quantum）。\n"
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


def generate_profile_from_semantics(
    user_id: str,
    project_id: str | None,
    semantic_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """根据若干条 semantic 记忆聚合生成结构化画像 JSON。

    `semantic_items` 预期形如：[{"text": ..., "tags": [...], "importance": ...}, ...]
    返回一个 Python dict，对应文档中定义的 profile 结构；调用方可直接返回或落库。
    """

    if not semantic_items:
        return {
            "user_id": user_id,
            "project_id": project_id,
            "communication_style": {},
            "interests": [],
            "risk_preference": None,
            "tools_and_habits": [],
            "social_relations": [],
            "project_facts": {},
            "lifestyle_and_habits": [],
            "thinking_and_values": {},
        }

    # 为避免 prompt 过长，仅截取前若干条（importance 已在上游排序）
    max_items = 40
    trimmed_items = semantic_items[:max_items]

    system_prompt = (
        "你是一个画像聚合助手，将若干条 semantic 记忆汇总为结构化用户画像 JSON。"  # noqa: E501
        "请基于给定的语义记忆，按照以下字段输出一个 JSON 对象（JSON 的 key 保持为下列英文单词，"  # noqa: E501
        "但所有中文可读内容一律使用简体中文描述）：\n"
        "- user_id: 字符串\n"
        "- project_id: 字符串或 null\n"
        "- communication_style: 对象，描述语气、语言、回答风格等（用中文描述）\n"
        "- interests: 字符串数组，描述长期兴趣与关注点（数组元素用中文，例如“量子物理”“Agent 架构设计”）\n"
        "- risk_preference: 字符串，描述大致决策/风险偏好（用中文）\n"
        "- tools_and_habits: 字符串数组，描述常用工具、工作/学习习惯（用中文）\n"
        "- social_relations: 字符串数组，描述重要的人物关系或协作模式（用中文）\n"
        "- project_facts: 对象，key 为项目 ID，value 为该项目的关键信息（如技术栈、设计原则等，内容用中文）\n"
        "- lifestyle_and_habits: 字符串数组，描述作息、生活习惯和生活领域的兴趣点（用中文）\n"
        "- thinking_and_values: 对象，描述思维方式与价值观，比如“理性批判 + 实用主义 + 合作性”，可包含 style/description/cooperation 等子字段（用中文）。\n"
        "请尽量基于提供的记忆推断，不要编造与记忆完全无关的内容；信息不足的字段可以给出简短的中文描述或使用空对象/空数组。"  # noqa: E501
    )

    user_prompt = (
        "下面是某个用户的一组 semantic 记忆条目，请基于这些条目生成上述结构化画像 JSON。"  # noqa: E501
        f"\n- user_id: {user_id}\n- project_id: {project_id or 'null'}\n\n"
        "【语义记忆条目（JSON 数组）】\n"
        f"{json.dumps(trimmed_items, ensure_ascii=False)}\n\n"
        "请只输出一个 JSON 对象，不要包含其他解释性文字。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = chat_completion(messages)

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # 确保至少包含 user_id / project_id 字段
            data.setdefault("user_id", user_id)
            data.setdefault("project_id", project_id)
            return data
    except json.JSONDecodeError:
        pass

    # 解析失败或返回非 dict 时，退化为一个空结构
    return {
        "user_id": user_id,
        "project_id": project_id,
        "communication_style": {},
        "interests": [],
        "risk_preference": None,
        "tools_and_habits": [],
        "social_relations": [],
        "project_facts": {},
        "lifestyle_and_habits": [],
        "thinking_and_values": {},
    }


def extract_knowledge_insights(
    project_id: str | None,
    semantic_items: List[Dict[str, Any]],
    recent_conversations: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """从 semantic 记忆和对话中提取可复用的知识洞察
    
    这些知识将用于丰富知识库，提升后续回答质量。
    
    Args:
        project_id: 项目 ID
        semantic_items: 语义记忆条目
        recent_conversations: 近期对话记录（可选）
        
    Returns:
        知识洞察列表，每项包含 content/category/confidence/tags
    """
    if not semantic_items:
        return []
    
    max_items = 30
    trimmed_items = semantic_items[:max_items]
    
    system_prompt = (
        "你是一个知识提取专家，负责从用户对话和记忆中提取可复用的知识点。\n"
        "这些知识将用于丰富知识库，帮助后续回答类似问题。\n\n"
        "请提取以下类型的知识：\n"
        "1) domain: 领域专业知识（如八字排盘规则、法律条款解释）\n"
        "2) skill: 技能技巧（如沟通技巧、问题解决方法）\n"
        "3) fact: 事实信息（如产品特性、历史事件）\n"
        "4) pattern: 模式规律（如用户常见问题、最佳实践）\n"
        "5) general: 通用知识\n\n"
        "输出 JSON 数组，每个元素：\n"
        '{"content": "知识点内容", "category": "domain/skill/fact/pattern/general", '
        '"confidence": 0.7-1.0, "tags": ["tag1", "tag2"]}\n\n'
        "注意：\n"
        "- 只提取可复用、有普遍价值的知识\n"
        "- 不要提取个人隐私信息\n"
        "- confidence 表示知识的可靠程度\n"
        "- 如果没有可提取的知识，返回空数组 []"
    )
    
    user_prompt = (
        f"项目 ID: {project_id or '通用'}\n\n"
        "【语义记忆条目】\n"
        f"{json.dumps(trimmed_items, ensure_ascii=False)}\n\n"
        "请提取可复用的知识点，只输出 JSON 数组。"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = chat_completion(messages)
    
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict) and "content" in x]
        return []
    except json.JSONDecodeError:
        return []


def generate_self_reflection(
    user_input: str,
    assistant_response: str,
    intent_category: str | None = None,
    tool_used: str | None = None,
) -> Dict[str, Any]:
    """对单次对话进行质量评估和自反省
    
    Args:
        user_input: 用户输入
        assistant_response: 助手回复
        intent_category: 意图类别
        tool_used: 使用的工具
        
    Returns:
        反省结果，包含 satisfaction_score/problem_solved/strengths/weaknesses/suggestions
    """
    system_prompt = (
        "你是一个对话质量分析专家。分析助手的回复质量，给出客观评估。\n\n"
        "请以 JSON 格式返回：\n"
        '{"satisfaction_score": 1-10, "completeness": "complete/partial/incomplete", '
        '"problem_solved": true/false, "strengths": ["优点1"], "weaknesses": ["缺点1"], '
        '"suggestions": ["建议1"], "summary": "一句话总结"}\n\n'
        "评分标准：\n"
        "- 10分：完美回答，超出预期\n"
        "- 7-9分：很好，基本满足需求\n"
        "- 4-6分：一般，部分满足需求\n"
        "- 1-3分：较差，未能满足需求\n\n"
        "只返回 JSON。"
    )
    
    user_prompt = (
        f"【用户问题】\n{user_input[:500]}\n\n"
        f"【助手回复】\n{assistant_response[:1000]}\n\n"
        f"【意图类别】{intent_category or '未知'}\n"
        f"【使用工具】{tool_used or '无'}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = chat_completion(messages)
    
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    
    return {
        "satisfaction_score": 5,
        "completeness": "partial",
        "problem_solved": False,
        "strengths": [],
        "weaknesses": [],
        "suggestions": [],
        "summary": "评估失败",
    }


def generate_profile_with_reflection(
    user_id: str,
    project_id: str | None,
    semantic_items: List[Dict[str, Any]],
    recent_reflections: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """生成画像的同时进行自我反省（复用同一次 LLM 调用）
    
    Args:
        user_id: 用户 ID
        project_id: 项目 ID
        semantic_items: 语义记忆
        recent_reflections: 近期反省记录（用于参考）
        
    Returns:
        包含 profile 和 reflection_summary 的结果
    """
    if not semantic_items:
        return {
            "profile": generate_profile_from_semantics(user_id, project_id, []),
            "reflection_summary": None,
            "knowledge_insights": [],
        }
    
    max_items = 35
    trimmed_items = semantic_items[:max_items]
    
    system_prompt = (
        "你是一个综合分析助手，需要同时完成三项任务：\n"
        "1) 生成用户画像\n"
        "2) 反省近期对话质量\n"
        "3) 提取可复用知识\n\n"
        "请输出一个 JSON 对象，包含三个字段：\n"
        "- profile: 用户画像对象（communication_style/interests/risk_preference/...）\n"
        "- reflection_summary: 对象，包含 avg_score(平均满意度)/common_issues(常见问题)/improvement_direction(改进方向)\n"
        "- knowledge_insights: 数组，每项 {content, category, confidence}\n\n"
        "只输出 JSON，不要其他内容。"
    )
    
    user_prompt = (
        f"- user_id: {user_id}\n- project_id: {project_id or 'null'}\n\n"
        "【语义记忆条目】\n"
        f"{json.dumps(trimmed_items, ensure_ascii=False)}\n\n"
        "请生成画像、反省总结和知识洞察。"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = chat_completion(messages, max_tokens=1500)
    
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            profile = data.get("profile", {})
            profile.setdefault("user_id", user_id)
            profile.setdefault("project_id", project_id)
            return {
                "profile": profile,
                "reflection_summary": data.get("reflection_summary"),
                "knowledge_insights": data.get("knowledge_insights", []),
            }
    except json.JSONDecodeError:
        pass
    
    # 降级：只生成画像
    return {
        "profile": generate_profile_from_semantics(user_id, project_id, semantic_items),
        "reflection_summary": None,
        "knowledge_insights": [],
    }


def generate_memories_unified(
    session_id: str,
    conversation_text: str,
    user_id: str | None = None,
    project_id: str | None = None,
    include_prompt_suggestions: bool = False,
) -> Dict[str, Any]:
    """统一记忆生成：一次 LLM 调用同时生成 episodic + semantic + prompt 建议
    
    优化：原来需要 2-3 次 LLM 调用，现在合并为 1 次
    
    Args:
        session_id: 会话 ID
        conversation_text: 对话内容
        user_id: 用户 ID
        project_id: 项目 ID
        include_prompt_suggestions: 是否包含 prompt 优化建议（受 PROMPT_EVOLUTION_ENABLED 控制）
    
    Returns:
        {
            "episodic": "情节总结文本",
            "semantic": [{"text": "...", "category": "...", "tags": [...]}],
            "prompt_suggestions": [{"prompt_type": "...", "suggestion": "..."}]  # 可选
        }
    """
    if len(conversation_text) > 4000:
        conversation_text = conversation_text[-4000:]
    
    # 是否真正启用 prompt 建议
    enable_prompt_suggestions = include_prompt_suggestions and PROMPT_EVOLUTION_ENABLED
    
    prompt_suggestion_part = ""
    if enable_prompt_suggestions:
        prompt_suggestion_part = """
4) prompt_suggestions: 数组（可选），如果发现当前系统 prompt 不太适合该用户，给出优化建议：
   - prompt_type: 建议修改的 prompt 类型（response_system / intent_system）
   - suggestion: 具体建议（如"用户喜欢简洁回复，建议精简答案"）
   如果没有建议，返回空数组 []。"""

    system_prompt = f"""你是一个智能记忆管理助手，负责从对话中提取多种类型的记忆。

请分析对话内容，一次性返回以下内容（JSON 格式）：

1) episodic: 字符串，情节总结（2-4句话），描述这次对话主要做了什么、关键决策
2) semantic: 数组，提取的长期记忆（用户偏好、事实），每条包含：
   - text: 一句话结论
   - category: 分类（identity_profile/communication_style/interests/work_style/values）
   - tags: 标签数组
   - importance: 重要性 0.5-1.0
3) should_update_profile: 布尔值，是否建议更新用户画像（semantic 有重要发现时为 true）
{prompt_suggestion_part}

输出示例：
{{
  "episodic": "用户咨询了八字命理，讨论了大运走势...",
  "semantic": [
    {{"text": "用户对命理感兴趣", "category": "interests", "tags": ["interest:divination"], "importance": 0.7}}
  ],
  "should_update_profile": false,
  "prompt_suggestions": []
}}

注意：
- 如果对话信息不足，semantic 可以返回空数组
- 不要编造与对话无关的内容
- 只输出 JSON，不要其他文字"""

    user_prompt = f"""请分析以下对话，提取记忆：

会话 ID: {session_id}
用户 ID: {user_id or "未知"}
项目 ID: {project_id or "未知"}

【对话内容】
{conversation_text}

请只输出 JSON："""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = chat_completion(messages, max_tokens=1000)
    
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {
                "episodic": data.get("episodic", ""),
                "semantic": data.get("semantic", []),
                "should_update_profile": data.get("should_update_profile", False),
                "prompt_suggestions": data.get("prompt_suggestions", []) if enable_prompt_suggestions else [],
            }
    except json.JSONDecodeError:
        pass
    
    # 解析失败时的降级处理
    return {
        "episodic": "",
        "semantic": [],
        "should_update_profile": False,
        "prompt_suggestions": [],
    }
