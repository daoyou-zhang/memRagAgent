"""道友认知服务 - Prompt 配置

支持多行业/多项目的 Prompt 配置：
- 默认 Prompt（通用）
- 行业 Prompt（八字命理、法律咨询、医疗问诊等）
- 项目 Prompt（按 project_id 查找）

配置优先级: 请求参数 > 项目配置 > 行业配置 > 环境变量 > 默认值
"""
import os
from typing import Optional, Dict
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 默认 Prompt 模板（通用）
# ============================================================

DEFAULT_INTENT_SYSTEM_PROMPT = """你是一个意图分析专家。分析用户输入，提取意图信息。

请以 JSON 格式返回，包含以下字段：
{
  "category": "意图类别，如 greeting/question/divination/legal/medical/task/chat/search/other",
  "confidence": 0.0-1.0 的置信度,
  "entities": [{"type": "实体类型", "value": "实体值"}],
  "summary": "用户意图的简短总结",
  "needs_tool": true/false 是否需要调用工具,
  "suggested_tools": ["可能需要的工具名称"]
}

注意：
- divination: 命理、八字、占卜相关
- legal: 法律咨询相关
- medical: 医疗健康相关

只返回 JSON，不要其他内容。"""

DEFAULT_INTENT_USER_TEMPLATE = """分析以下用户输入的意图：

用户输入: {input}
上下文信息: {context}"""


DEFAULT_RESPONSE_SYSTEM_PROMPT = """你是道友，一个智能认知助手。

你具备以下能力：
- 理解用户意图并给出准确回答
- 结合用户画像提供个性化服务
- 利用历史对话保持上下文连贯
- 基于检索到的相关记忆增强回答

请用自然、友好的方式回答用户问题。"""

DEFAULT_RESPONSE_USER_TEMPLATE = """请回答用户的问题。

{profile_section}
{memory_section}
{rag_section}

用户问题: {input}"""


# ============================================================
# 行业 Prompt 模板
# ============================================================

# 八字命理行业
BAZI_RESPONSE_SYSTEM_PROMPT = """你是道友，一位精通八字命理的专业顾问。

你的专业能力：
- 精通四柱八字、十神关系、五行生克
- 能够解读大运流年、分析命局格局
- 结合现代语言解释传统命理知识
- 给出有建设性的人生建议

注意事项：
- 基于工具返回的八字数据进行专业解读
- 用通俗易懂的语言解释命理术语
- 避免过于绝对的断言，强调命理仅供参考
- 保持积极正面的引导"""

# 法律咨询行业
LEGAL_RESPONSE_SYSTEM_PROMPT = """你是道友，一位专业的法律顾问助手。

你的专业能力：
- 熟悉中国法律法规体系
- 能够提供法律问题的初步分析
- 引导用户了解相关法律条款
- 建议何时需要寻求专业律师帮助

注意事项：
- 基于检索到的法律知识回答
- 明确说明这是法律咨询参考，非正式法律意见
- 涉及重大法律问题建议寻求专业律师
- 保持客观中立"""

# 医疗健康行业
MEDICAL_RESPONSE_SYSTEM_PROMPT = """你是道友，一位健康咨询助手。

你的专业能力：
- 了解常见疾病的基本知识
- 能够提供健康生活建议
- 引导用户了解健康知识

注意事项：
- 明确说明这不是医疗诊断
- 任何疾病症状都建议就医检查
- 不推荐具体药物
- 关注用户心理健康"""


# 行业配置映射
INDUSTRY_PROMPTS: Dict[str, Dict[str, str]] = {
    "bazi": {
        "response_system": BAZI_RESPONSE_SYSTEM_PROMPT,
    },
    "divination": {
        "response_system": BAZI_RESPONSE_SYSTEM_PROMPT,
    },
    "legal": {
        "response_system": LEGAL_RESPONSE_SYSTEM_PROMPT,
    },
    "medical": {
        "response_system": MEDICAL_RESPONSE_SYSTEM_PROMPT,
    },
}

# 项目配置映射（可从数据库加载，这里先用代码配置）
PROJECT_PROMPTS: Dict[str, Dict[str, str]] = {
    # "legal_project": {
    #     "response_system": LEGAL_RESPONSE_SYSTEM_PROMPT,
    # },
}


# ============================================================
# 从环境变量加载配置
# ============================================================

def _get_env_prompt(key: str, default: str) -> str:
    """从环境变量获取 prompt，支持 \n 转换为真正的换行"""
    value = os.getenv(key, default)
    return value.replace("\\n", "\n")


@dataclass
class PromptConfig:
    """Prompt configuration container."""
    
    # 意图理解
    intent_system_prompt: str
    intent_user_template: str
    
    # 内容生成
    response_system_prompt: str
    response_user_template: str
    
    @classmethod
    def from_env(cls) -> "PromptConfig":
        """Load prompts from environment variables."""
        return cls(
            intent_system_prompt=_get_env_prompt(
                "PROMPT_INTENT_SYSTEM", DEFAULT_INTENT_SYSTEM_PROMPT
            ),
            intent_user_template=_get_env_prompt(
                "PROMPT_INTENT_USER", DEFAULT_INTENT_USER_TEMPLATE
            ),
            response_system_prompt=_get_env_prompt(
                "PROMPT_RESPONSE_SYSTEM", DEFAULT_RESPONSE_SYSTEM_PROMPT
            ),
            response_user_template=_get_env_prompt(
                "PROMPT_RESPONSE_USER", DEFAULT_RESPONSE_USER_TEMPLATE
            ),
        )
    
    def override(
        self,
        intent_system: Optional[str] = None,
        intent_user: Optional[str] = None,
        response_system: Optional[str] = None,
        response_user: Optional[str] = None,
    ) -> "PromptConfig":
        """Create a new config with optional overrides."""
        return PromptConfig(
            intent_system_prompt=intent_system or self.intent_system_prompt,
            intent_user_template=intent_user or self.intent_user_template,
            response_system_prompt=response_system or self.response_system_prompt,
            response_user_template=response_user or self.response_user_template,
        )


# 全局配置实例（从环境变量加载）
_prompt_config: Optional[PromptConfig] = None


def get_prompt_config() -> PromptConfig:
    """Get the global prompt configuration (singleton)."""
    global _prompt_config
    if _prompt_config is None:
        _prompt_config = PromptConfig.from_env()
    return _prompt_config


def reload_prompt_config() -> PromptConfig:
    """Force reload prompts from environment (useful after .env changes)."""
    global _prompt_config
    _prompt_config = PromptConfig.from_env()
    return _prompt_config


def get_prompt_for_industry(industry: str) -> PromptConfig:
    """根据行业获取 Prompt 配置
    
    Args:
        industry: 行业标识（divination/legal/medical 等）
        
    Returns:
        该行业的 Prompt 配置
    """
    base_config = get_prompt_config()
    
    if industry in INDUSTRY_PROMPTS:
        industry_config = INDUSTRY_PROMPTS[industry]
        return base_config.override(
            response_system=industry_config.get("response_system"),
            response_user=industry_config.get("response_user"),
            intent_system=industry_config.get("intent_system"),
            intent_user=industry_config.get("intent_user"),
        )
    
    return base_config


def get_prompt_for_project(project_id: str) -> PromptConfig:
    """根据项目 ID 获取 Prompt 配置
    
    Args:
        project_id: 项目 ID
        
    Returns:
        该项目的 Prompt 配置
    """
    base_config = get_prompt_config()
    
    if project_id in PROJECT_PROMPTS:
        project_config = PROJECT_PROMPTS[project_id]
        return base_config.override(
            response_system=project_config.get("response_system"),
            response_user=project_config.get("response_user"),
            intent_system=project_config.get("intent_system"),
            intent_user=project_config.get("intent_user"),
        )
    
    return base_config


def get_prompt_for_context(
    project_id: Optional[str] = None,
    industry: Optional[str] = None,
) -> PromptConfig:
    """根据上下文获取最合适的 Prompt 配置
    
    优先级: 项目配置 > 行业配置 > 默认配置
    
    Args:
        project_id: 项目 ID
        industry: 行业标识（通常从意图分析的 category 获取）
        
    Returns:
        最合适的 Prompt 配置
    """
    # 优先使用项目配置
    if project_id and project_id in PROJECT_PROMPTS:
        return get_prompt_for_project(project_id)
    
    # 其次使用行业配置
    if industry and industry in INDUSTRY_PROMPTS:
        return get_prompt_for_industry(industry)
    
    # 默认配置
    return get_prompt_config()
