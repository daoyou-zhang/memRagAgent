"""Prompt 管理 API

提供 Prompt 配置的查询和管理
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config.prompts import (
    get_prompt_config,
    INDUSTRY_PROMPTS,
    PROJECT_PROMPTS,
    DEFAULT_INTENT_SYSTEM_PROMPT,
    DEFAULT_RESPONSE_SYSTEM_PROMPT,
)


router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class PromptConfigResponse(BaseModel):
    """Prompt 配置响应"""
    intent_system_prompt: str
    intent_user_prompt: str
    response_system_prompt: str
    response_user_prompt: str


class IndustryPromptResponse(BaseModel):
    """行业 Prompt 响应"""
    industry: str
    system_prompt: str


class ProjectPromptResponse(BaseModel):
    """项目 Prompt 响应"""
    project_id: str
    system_prompt: str


# ============================================================
# API 端点
# ============================================================

@router.get("/default", response_model=PromptConfigResponse)
async def get_default_prompts():
    """获取默认 Prompt 配置"""
    config = get_prompt_config()
    return PromptConfigResponse(
        intent_system_prompt=config.intent_system_prompt,
        intent_user_prompt=config.intent_user_prompt,
        response_system_prompt=config.response_system_prompt,
        response_user_prompt=config.response_user_prompt,
    )


@router.get("/industries", response_model=List[IndustryPromptResponse])
async def list_industry_prompts():
    """获取所有行业 Prompt"""
    return [
        IndustryPromptResponse(industry=k, system_prompt=v[:200] + "..." if len(v) > 200 else v)
        for k, v in INDUSTRY_PROMPTS.items()
    ]


@router.get("/industries/{industry}")
async def get_industry_prompt(industry: str):
    """获取指定行业的 Prompt"""
    if industry not in INDUSTRY_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Industry '{industry}' not found")
    return {
        "industry": industry,
        "system_prompt": INDUSTRY_PROMPTS[industry],
    }


@router.get("/projects", response_model=List[ProjectPromptResponse])
async def list_project_prompts():
    """获取所有项目 Prompt"""
    return [
        ProjectPromptResponse(project_id=k, system_prompt=v[:200] + "..." if len(v) > 200 else v)
        for k, v in PROJECT_PROMPTS.items()
    ]


@router.get("/projects/{project_id}")
async def get_project_prompt(project_id: str):
    """获取指定项目的 Prompt"""
    if project_id not in PROJECT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return {
        "project_id": project_id,
        "system_prompt": PROJECT_PROMPTS[project_id],
    }


@router.get("/templates")
async def list_templates():
    """获取 Prompt 模板列表"""
    return {
        "templates": {
            "intent_system": {
                "name": "意图理解系统提示",
                "default": DEFAULT_INTENT_SYSTEM_PROMPT[:300] + "...",
            },
            "response_system": {
                "name": "回复生成系统提示",
                "default": DEFAULT_RESPONSE_SYSTEM_PROMPT[:300] + "...",
            },
        },
        "industries": list(INDUSTRY_PROMPTS.keys()),
        "projects": list(PROJECT_PROMPTS.keys()),
    }


@router.post("/preview")
async def preview_prompt(
    user_input: str,
    industry: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """预览最终 Prompt（不调用 LLM）"""
    from ..config.prompts import get_prompt_for_context
    
    base_config = get_prompt_config()
    final_prompt = get_prompt_for_context(industry, project_id)
    
    return {
        "user_input": user_input,
        "industry": industry,
        "project_id": project_id,
        "final_system_prompt": final_prompt,
        "intent_system_prompt": base_config.intent_system_prompt[:500] + "...",
    }
