"""道友认知服务 - Prompt 生成原则

本文件定义【Prompt 生成原则】：
- 这些是所有 Prompt 必须遵守的核心规则
- 不包含任何领域/行业特定内容
- 领域 Prompt 存储在数据库 prompt_configs 表，支持自进化

架构：
┌─────────────────────────────────────────────────────────┐
│  请求参数 (最高优先级)                                    │
├─────────────────────────────────────────────────────────┤
│  数据库 project 配置                                      │
├─────────────────────────────────────────────────────────┤
│  数据库 category/industry 配置                           │
├─────────────────────────────────────────────────────────┤
│  代码原则 Prompt (本文件，最低优先级)                     │
└─────────────────────────────────────────────────────────┘

数据库 Prompt 生成时，应遵循本文件定义的 PROMPT_PRINCIPLES。
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv

# 加载配置
_backend_root = Path(__file__).parent.parent.parent
load_dotenv(_backend_root / ".env")
load_dotenv()


# ============================================================
# Prompt 生成原则（所有 Prompt 必须遵守）
# ============================================================

PROMPT_PRINCIPLES = """
【道友 Prompt 生成原则】

1. 身份原则
   - 始终以"道友"自称
   - 绝不暴露底层模型名称（DeepSeek、GPT、Claude 等）
   - 如被问及身份，回答"我是道友智能助手"

2. 合规原则
   - 不生成违反法律法规的内容
   - 不生成歧视、仇恨、暴力相关内容
   - 涉及敏感话题时保持中立客观

3. 向善原则
   - 引导用户积极正面思考
   - 避免绝对化断言，保持开放性
   - 尊重用户隐私和个人选择

4. 专业原则
   - 基于事实和检索到的知识回答
   - 不确定时明确说明局限性
   - 重大问题建议寻求专业人士帮助

5. 交互原则
   - 语言自然友好，避免机械感
   - 结合用户画像提供个性化服务
   - 保持对话上下文连贯
"""


# ============================================================
# 基础 Prompt 模板（通用结构）
# ============================================================

DEFAULT_INTENT_SYSTEM_PROMPT = """你是一个意图分析专家。分析用户输入，提取意图信息。

请以 JSON 格式返回，包含以下字段：
{
  "category": "意图类别",
  "confidence": 0.0-1.0 的置信度,
  "entities": [{"type": "实体类型", "value": "实体值"}],
  "summary": "用户意图的简短总结",
  "needs_tool": true/false 是否需要调用工具,
  "suggested_tools": ["可能需要的工具名称"]
}

只返回 JSON，不要其他内容。"""

DEFAULT_INTENT_USER_TEMPLATE = """分析以下用户输入的意图：

用户输入: {input}
上下文信息: {context}"""


DEFAULT_RESPONSE_SYSTEM_PROMPT = f"""你是道友，一个智能认知助手。

{PROMPT_PRINCIPLES}

请基于以上原则，用自然、友好的方式回答用户问题。"""

DEFAULT_RESPONSE_USER_TEMPLATE = """请回答用户的问题。

{profile_section}
{memory_section}
{rag_section}

用户问题: {input}"""


# ============================================================
# Prompt 生成辅助函数
# ============================================================

def build_domain_prompt(
    domain_name: str,
    domain_expertise: str,
    domain_guidelines: str,
) -> str:
    """生成领域 Prompt（数据库 Prompt 自进化时使用）
    
    Args:
        domain_name: 领域名称（如"八字命理"、"法律咨询"）
        domain_expertise: 领域专业能力描述
        domain_guidelines: 领域特定注意事项
        
    Returns:
        符合原则的领域 Prompt
    """
    return f"""你是道友，一位专业的{domain_name}助手。

你的专业能力：
{domain_expertise}

{PROMPT_PRINCIPLES}

领域特定注意事项：
{domain_guidelines}
"""


# ============================================================
# 从环境变量加载配置
# ============================================================

def _get_env_prompt(key: str, default: str) -> str:
    """从环境变量获取 prompt，支持 \n 转换为真正的换行"""
    value = os.getenv(key, default)
    return value.replace("\\n", "\n")


@dataclass
class PromptConfig:
    """Prompt 配置容器"""
    
    # 意图理解
    intent_system_prompt: str
    intent_user_template: str
    
    # 内容生成
    response_system_prompt: str
    response_user_template: str
    
    @classmethod
    def from_env(cls) -> "PromptConfig":
        """从环境变量加载配置"""
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
        """创建一个带覆盖值的新配置"""
        return PromptConfig(
            intent_system_prompt=intent_system or self.intent_system_prompt,
            intent_user_template=intent_user or self.intent_user_template,
            response_system_prompt=response_system or self.response_system_prompt,
            response_user_template=response_user or self.response_user_template,
        )


# ============================================================
# 全局配置
# ============================================================

_prompt_config: Optional[PromptConfig] = None


def get_prompt_config() -> PromptConfig:
    """获取全局 Prompt 配置（单例）
    
    返回基于原则的默认配置，实际使用时会被数据库配置覆盖
    """
    global _prompt_config
    if _prompt_config is None:
        _prompt_config = PromptConfig.from_env()
    return _prompt_config


def reload_prompt_config() -> PromptConfig:
    """强制重新加载配置"""
    global _prompt_config
    _prompt_config = PromptConfig.from_env()
    return _prompt_config


def get_principles() -> str:
    """获取 Prompt 生成原则（供 LLM 生成领域 Prompt 时参考）"""
    return PROMPT_PRINCIPLES
