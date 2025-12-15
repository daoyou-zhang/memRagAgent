from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PromptConfigBase(BaseModel):
    """公共字段模型，用于创建/更新 Prompt 配置。

    与数据库 prompt_configs 表字段保持一致，简化服务层交互。
    """

    category: Optional[str] = None
    project_id: Optional[str] = None
    agent_id: Optional[str] = None

    name: str
    description: Optional[str] = None

    intent_system_prompt: Optional[str] = None
    intent_user_template: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_template: Optional[str] = None

    enabled: Optional[bool] = True
    priority: Optional[int] = 0


class PromptConfigCreate(PromptConfigBase):
    """创建 Prompt 配置时使用的模型。"""

    pass


class PromptConfigUpdate(BaseModel):
    """更新 Prompt 配置时使用的模型。

    所有字段均可选，服务层会做局部更新。
    """

    category: Optional[str] = None
    project_id: Optional[str] = None
    agent_id: Optional[str] = None

    name: Optional[str] = None
    description: Optional[str] = None

    intent_system_prompt: Optional[str] = None
    intent_user_template: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_template: Optional[str] = None

    enabled: Optional[bool] = None
    priority: Optional[int] = None


class PromptConfigResponse(PromptConfigBase):
    """对外返回的 Prompt 配置模型。"""

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
