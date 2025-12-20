"""Prompt 进化 API

提供 Prompt 自进化的管理接口
"""
from flask import Blueprint, jsonify, request

from ..services.prompt_evolution import get_prompt_evolution_service

prompt_evolution_bp = Blueprint("prompt_evolution", __name__)


@prompt_evolution_bp.get("/pending")
def get_pending_evolutions():
    """获取待处理的进化建议"""
    user_id = request.args.get("user_id")
    project_id = request.args.get("project_id")
    limit = int(request.args.get("limit", 20))
    
    service = get_prompt_evolution_service()
    records = service.get_pending_evolutions(
        user_id=user_id,
        project_id=project_id,
        limit=limit,
    )
    
    return jsonify({
        "evolutions": records,
        "count": len(records),
    })


@prompt_evolution_bp.post("/<int:evolution_id>/apply")
def apply_evolution(evolution_id: int):
    """应用进化建议"""
    service = get_prompt_evolution_service()
    result = service.apply_evolution(evolution_id)
    
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@prompt_evolution_bp.post("/<int:evolution_id>/reject")
def reject_evolution(evolution_id: int):
    """拒绝进化建议"""
    data = request.get_json() or {}
    reason = data.get("reason", "")
    
    service = get_prompt_evolution_service()
    result = service.reject_evolution(evolution_id, reason)
    
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@prompt_evolution_bp.post("/<int:evolution_id>/evaluate")
def evaluate_evolution(evolution_id: int):
    """更新进化效果评估"""
    data = request.get_json() or {}
    score = float(data.get("score", 0.5))
    
    service = get_prompt_evolution_service()
    result = service.update_evaluation(evolution_id, score)
    
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@prompt_evolution_bp.post("/process")
def process_suggestions():
    """处理 LLM 返回的优化建议（内部调用）
    
    请求体:
    {
        "suggestions": [
            {
                "prompt_type": "response_system",
                "suggestion": "用户喜欢简洁回复",
                "proposed_change": "..."
            }
        ],
        "user_id": "xxx",
        "project_id": "yyy",
        "category": "divination",
        "trigger_type": "profile_aggregate",
        "trigger_job_id": 123
    }
    """
    data = request.get_json() or {}
    
    suggestions = data.get("suggestions", [])
    if not suggestions:
        return jsonify({"created_ids": [], "message": "No suggestions provided"})
    
    service = get_prompt_evolution_service()
    created_ids = service.process_llm_suggestions(
        suggestions=suggestions,
        user_id=data.get("user_id"),
        project_id=data.get("project_id"),
        category=data.get("category"),
        trigger_type=data.get("trigger_type", "manual"),
        trigger_job_id=data.get("trigger_job_id"),
    )
    
    return jsonify({
        "created_ids": created_ids,
        "count": len(created_ids),
        "message": f"Created {len(created_ids)} evolution records",
    })
