"""Prompt 自进化服务

职责：
- 从 LLM 返回中提取 prompt 优化建议
- 记录进化历史
- 应用/回滚 prompt 变更
- 评估进化效果

触发时机：
- profile_aggregate: 画像聚合时顺带返回建议
- reflection_low_score: 低分反馈积累触发
- manual: 手动触发优化
"""
import os
import json
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger

from sqlalchemy.orm import Session

from models.memory import PromptEvolutionHistory
from repository.db_session import SessionLocal

# Agent 服务 URL
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8000")


class PromptEvolutionService:
    """Prompt 进化服务"""
    
    def process_llm_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        trigger_type: str = "profile_aggregate",
        trigger_job_id: Optional[int] = None,
    ) -> List[int]:
        """处理 LLM 返回的 prompt 优化建议
        
        Args:
            suggestions: LLM 返回的建议列表，格式:
                [
                    {
                        "prompt_type": "response_system",
                        "suggestion": "用户喜欢简洁回复，建议...",
                        "proposed_change": "具体的 prompt 修改建议"
                    }
                ]
            user_id: 用户 ID（用户级优化）
            project_id: 项目 ID（项目级优化）
            category: 意图分类
            trigger_type: 触发类型
            trigger_job_id: 触发的 Job ID
            
        Returns:
            创建的进化记录 ID 列表
        """
        if not suggestions:
            return []
        
        db: Session = SessionLocal()
        created_ids = []
        
        try:
            for sugg in suggestions:
                prompt_type = sugg.get("prompt_type", "response_system")
                suggestion_text = sugg.get("suggestion", "")
                proposed_change = sugg.get("proposed_change", "")
                
                if not suggestion_text:
                    continue
                
                # 创建进化记录
                record = PromptEvolutionHistory(
                    user_id=user_id,
                    project_id=project_id,
                    category=category,
                    trigger_type=trigger_type,
                    trigger_reason=suggestion_text,
                    trigger_job_id=trigger_job_id,
                    prompt_type=prompt_type,
                    after_prompt=proposed_change if proposed_change else None,
                    suggestion=suggestion_text,
                    status="pending",
                )
                db.add(record)
                db.flush()
                created_ids.append(record.id)
            
            db.commit()
            return created_ids
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_pending_evolutions(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取待处理的进化建议"""
        db: Session = SessionLocal()
        try:
            q = db.query(PromptEvolutionHistory).filter(
                PromptEvolutionHistory.status == "pending"
            )
            if user_id:
                q = q.filter(PromptEvolutionHistory.user_id == user_id)
            if project_id:
                q = q.filter(PromptEvolutionHistory.project_id == project_id)
            
            records = q.order_by(PromptEvolutionHistory.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "project_id": r.project_id,
                    "category": r.category,
                    "trigger_type": r.trigger_type,
                    "trigger_reason": r.trigger_reason,
                    "prompt_type": r.prompt_type,
                    "suggestion": r.suggestion,
                    "after_prompt": r.after_prompt,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            db.close()
    
    def apply_evolution(self, evolution_id: int) -> Dict[str, Any]:
        """应用进化建议
        
        通过调用 daoyou_agent 的 Prompt API 创建/更新配置
        """
        db: Session = SessionLocal()
        try:
            record = db.query(PromptEvolutionHistory).filter(
                PromptEvolutionHistory.id == evolution_id
            ).first()
            
            if not record:
                return {"success": False, "error": "Evolution record not found"}
            
            if record.status != "pending":
                return {"success": False, "error": f"Cannot apply evolution with status: {record.status}"}
            
            # 保存当前 prompt 用于回滚
            before_prompt = self._get_current_prompt(record)
            record.before_prompt = before_prompt
            
            # 通过 API 应用新的 prompt
            apply_result = self._apply_prompt_via_api(record)
            
            if not apply_result.get("success"):
                return apply_result
            
            record.status = "applied"
            record.applied_at = datetime.now()
            db.commit()
            
            logger.info(f"进化建议 {evolution_id} 已应用")
            
            return {
                "success": True,
                "evolution_id": evolution_id,
                "status": "applied",
                "config_id": apply_result.get("config_id"),
                "message": "Evolution applied successfully",
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"应用进化建议失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def _get_current_prompt(self, record: PromptEvolutionHistory) -> Optional[str]:
        """获取当前 prompt（用于回滚）"""
        try:
            # 构建查询参数
            params = {}
            if record.category:
                params["category"] = record.category
            if record.project_id:
                params["project_id"] = record.project_id
            
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{AGENT_SERVICE_URL}/api/v1/prompts/default",
                    params=params
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # 根据 prompt_type 获取对应字段
                    prompt_type = record.prompt_type or "response_system"
                    return data.get(f"{prompt_type}_prompt", "")
        except Exception as e:
            logger.warning(f"获取当前 prompt 失败: {e}")
        return None
    
    def _apply_prompt_via_api(self, record: PromptEvolutionHistory) -> Dict[str, Any]:
        """通过 API 应用 prompt 配置"""
        try:
            # 构建配置名称
            config_name = f"evolution_{record.id}"
            if record.user_id:
                config_name = f"user_{record.user_id}_{config_name}"
            elif record.project_id:
                config_name = f"project_{record.project_id}_{config_name}"
            
            # 构建请求体
            payload = {
                "category": record.category or "evolved",
                "project_id": record.project_id,
                "name": config_name,
                "description": f"自进化生成 - {record.trigger_reason[:100] if record.trigger_reason else ''}",
            }
            
            # 根据 prompt_type 设置对应字段
            prompt_type = record.prompt_type or "response_system"
            if record.after_prompt:
                if "intent" in prompt_type:
                    payload["intent_system_prompt"] = record.after_prompt
                else:
                    payload["response_system_prompt"] = record.after_prompt
            
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{AGENT_SERVICE_URL}/api/v1/prompts/configs",
                    json=payload
                )
                
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    return {
                        "success": True,
                        "config_id": data.get("id"),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API 返回 {resp.status_code}: {resp.text}",
                    }
                    
        except Exception as e:
            logger.error(f"调用 Prompt API 失败: {e}")
            return {"success": False, "error": str(e)}
    
    def reject_evolution(self, evolution_id: int, reason: str = "") -> Dict[str, Any]:
        """拒绝进化建议"""
        db: Session = SessionLocal()
        try:
            record = db.query(PromptEvolutionHistory).filter(
                PromptEvolutionHistory.id == evolution_id
            ).first()
            
            if not record:
                return {"success": False, "error": "Evolution record not found"}
            
            record.status = "rejected"
            if reason:
                record.trigger_reason = f"{record.trigger_reason}\n[拒绝原因] {reason}"
            db.commit()
            
            return {"success": True, "evolution_id": evolution_id, "status": "rejected"}
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def update_evaluation(
        self,
        evolution_id: int,
        score: float,
        increment_count: bool = True,
    ) -> Dict[str, Any]:
        """更新进化效果评估"""
        db: Session = SessionLocal()
        try:
            record = db.query(PromptEvolutionHistory).filter(
                PromptEvolutionHistory.id == evolution_id
            ).first()
            
            if not record:
                return {"success": False, "error": "Evolution record not found"}
            
            # 增量平均
            if record.evaluation_count > 0 and record.evaluation_score is not None:
                total = record.evaluation_score * record.evaluation_count + score
                record.evaluation_count += 1 if increment_count else 0
                record.evaluation_score = total / record.evaluation_count
            else:
                record.evaluation_score = score
                record.evaluation_count = 1
            
            db.commit()
            
            return {
                "success": True,
                "evolution_id": evolution_id,
                "new_score": record.evaluation_score,
                "count": record.evaluation_count,
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()


# 单例
_prompt_evolution_service: Optional[PromptEvolutionService] = None


def get_prompt_evolution_service() -> PromptEvolutionService:
    global _prompt_evolution_service
    if _prompt_evolution_service is None:
        _prompt_evolution_service = PromptEvolutionService()
    return _prompt_evolution_service
