"""Prompt 配置数据模型

支持从数据库动态加载 Prompt 配置
表结构定义在 db/02_prompt_configs.sql
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# Pydantic 请求/响应模型
# ============================================================

class PromptConfigCreate(BaseModel):
    """创建 Prompt 配置请求"""
    category: Optional[str] = Field(None, description="行业分类: divination/legal/medical")
    project_id: Optional[str] = Field(None, description="项目 ID")
    name: str = Field(..., description="配置名称")
    description: Optional[str] = None
    intent_system_prompt: Optional[str] = None
    intent_user_template: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_template: Optional[str] = None
    enabled: bool = True
    priority: int = 0


class PromptConfigUpdate(BaseModel):
    """更新 Prompt 配置请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    intent_system_prompt: Optional[str] = None
    intent_user_template: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_template: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class PromptConfigResponse(BaseModel):
    """Prompt 配置响应"""
    id: int
    category: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    intent_system_prompt: Optional[str] = None
    intent_user_template: Optional[str] = None
    response_system_prompt: Optional[str] = None
    response_user_template: Optional[str] = None
    enabled: bool = True
    priority: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
