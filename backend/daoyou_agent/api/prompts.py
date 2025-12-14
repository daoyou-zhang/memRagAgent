"""Prompt 管理 API

提供 Prompt 配置的查询和 CRUD 管理
- 原则配置：代码中定义的核心原则（prompts.py）
- 领域配置：数据库 prompt_configs 表，支持自进化
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException

from ..config.prompts import (
    get_prompt_config,
    get_principles,
    build_domain_prompt,
    PROMPT_PRINCIPLES,
)
from ..models.prompt_config import PromptConfigCreate, PromptConfigUpdate, PromptConfigResponse
from ..services.prompt_service import get_prompt_service


router = APIRouter()


# ============================================================
# 原则配置查询（代码中定义，不可变）
# ============================================================

@router.get("/principles")
async def get_prompt_principles():
    """获取 Prompt 生成原则
    
    这些原则是所有 Prompt 必须遵守的核心规则，
    在生成新的领域 Prompt 时应参考这些原则。
    """
    return {
        "principles": PROMPT_PRINCIPLES,
        "description": "所有 Prompt 必须遵守的核心原则",
    }


@router.get("/default")
async def get_default_prompts():
    """获取默认 Prompt 配置（基于原则的基础模板）"""
    config = get_prompt_config()
    return {
        "intent_system_prompt": config.intent_system_prompt,
        "intent_user_template": config.intent_user_template,
        "response_system_prompt": config.response_system_prompt,
        "response_user_template": config.response_user_template,
    }


@router.get("/industries")
async def list_industry_prompts():
    """获取所有领域 Prompt（从数据库）"""
    service = get_prompt_service()
    configs = service.list_all(enabled_only=True)
    
    # 按 category 分组
    industries = {}
    for c in configs:
        cat = c.get("category")
        if cat and cat not in industries:
            industries[cat] = {
                "category": cat,
                "name": c.get("name"),
                "response_system_prompt": (c.get("response_system_prompt") or "")[:200] + "...",
            }
    
    return list(industries.values())


@router.get("/industries/{industry}")
async def get_industry_prompt(industry: str):
    """获取指定领域的 Prompt"""
    service = get_prompt_service()
    config = service.get_by_category(industry)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"领域 '{industry}' 配置不存在，请先创建")
    
    return {
        "industry": industry,
        "config": config,
    }


@router.get("/templates")
async def list_templates():
    """获取 Prompt 模板概览"""
    service = get_prompt_service()
    configs = service.list_all()
    
    categories = list(set(c.get("category") for c in configs if c.get("category")))
    projects = list(set(c.get("project_id") for c in configs if c.get("project_id")))
    
    return {
        "principles": "使用 GET /principles 查看",
        "categories": categories,
        "projects": projects,
        "total_configs": len(configs),
    }


@router.post("/preview")
async def preview_prompt(
    user_input: str,
    category: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """预览最终 Prompt（展示优先级合并结果）"""
    service = get_prompt_service()
    base_config = get_prompt_config()
    
    # 模拟优先级合并
    final_response = base_config.response_system_prompt
    source = "default"
    
    if category:
        db_config = service.get_by_category(category)
        if db_config and db_config.get("response_system_prompt"):
            final_response = db_config["response_system_prompt"]
            source = f"database:category:{category}"
    
    if project_id:
        db_config = service.get_by_project(project_id)
        if db_config and db_config.get("response_system_prompt"):
            final_response = db_config["response_system_prompt"]
            source = f"database:project:{project_id}"
    
    return {
        "user_input": user_input,
        "category": category,
        "project_id": project_id,
        "source": source,
        "final_response_system_prompt": final_response[:500] + "..." if len(final_response) > 500 else final_response,
    }


@router.post("/generate")
async def generate_domain_prompt(
    domain_name: str,
    domain_expertise: str,
    domain_guidelines: str,
):
    """生成符合原则的领域 Prompt（辅助工具）
    
    根据原则自动生成领域 Prompt，可以直接保存到数据库。
    """
    prompt = build_domain_prompt(domain_name, domain_expertise, domain_guidelines)
    return {
        "domain_name": domain_name,
        "generated_prompt": prompt,
        "hint": "可以将此 prompt 通过 POST /configs 保存到数据库",
    }


# ============================================================
# 数据库 CRUD（自定义配置）
# ============================================================

@router.get("/configs", response_model=List[PromptConfigResponse])
async def list_configs(enabled_only: bool = False):
    """获取所有自定义 Prompt 配置（数据库）"""
    service = get_prompt_service()
    configs = service.list_all(enabled_only=enabled_only)
    return [PromptConfigResponse(**c) for c in configs]


@router.get("/configs/{config_id}", response_model=PromptConfigResponse)
async def get_config(config_id: int):
    """根据 ID 获取配置"""
    service = get_prompt_service()
    config = service.get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"配置 ID={config_id} 不存在")
    return PromptConfigResponse(**config)


@router.get("/configs/category/{category}")
async def get_config_by_category(category: str):
    """根据领域获取配置"""
    service = get_prompt_service()
    config = service.get_by_category(category)
    if not config:
        raise HTTPException(
            status_code=404, 
            detail=f"领域 '{category}' 配置不存在，请使用 POST /configs 创建"
        )
    return {"source": "database", "config": config}


@router.get("/configs/project/{project_id}")
async def get_config_by_project(project_id: str):
    """根据项目获取自定义配置"""
    service = get_prompt_service()
    config = service.get_by_project(project_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"项目 '{project_id}' 配置不存在")
    return config


@router.post("/configs", response_model=PromptConfigResponse)
async def create_config(data: PromptConfigCreate):
    """创建 Prompt 配置
    
    category 和 project_id 至少填一个
    """
    if not data.category and not data.project_id:
        raise HTTPException(status_code=400, detail="category 和 project_id 至少填一个")
    
    service = get_prompt_service()
    
    try:
        config = service.create(data)
        if not config:
            raise HTTPException(status_code=500, detail="创建失败")
        return PromptConfigResponse(**config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/configs/{config_id}", response_model=PromptConfigResponse)
async def update_config(config_id: int, data: PromptConfigUpdate):
    """更新 Prompt 配置"""
    service = get_prompt_service()
    
    # 检查是否存在
    existing = service.get_by_id(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"配置 ID={config_id} 不存在")
    
    try:
        config = service.update(config_id, data)
        return PromptConfigResponse(**config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int):
    """删除 Prompt 配置"""
    service = get_prompt_service()
    
    if not service.delete(config_id):
        raise HTTPException(status_code=404, detail=f"配置 ID={config_id} 不存在")
    
    return {"message": f"配置 ID={config_id} 已删除"}
