from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from ..models.ai_prompt import AIPrompt

class AIPromptService:
    @staticmethod
    def get_prompt_by_service_and_level(
        db: Session, 
        service_key: str, 
        level: int, 
        prompt_type: str = "chat"
    ) -> Optional[AIPrompt]:
        """根据服务类型、等级和prompt类型获取对应的prompt"""
        query = text("""
            SELECT id, service_key, level, prompt_type, system_prompt, user_prompt_template, 
                   is_active, priority, created_at, updated_at
            FROM ai_prompts
            WHERE service_key = :service_key 
              AND level = :level 
              AND prompt_type = :prompt_type
              AND is_active = true
            ORDER BY priority DESC
            LIMIT 1
        """)
        result = db.execute(query, {
            "service_key": service_key,
            "level": level,
            "prompt_type": prompt_type
        })
        row = result.fetchone()
        
        if row:
            row_dict = dict(row._mapping)
            return AIPrompt(**row_dict)
        return None
    
    @staticmethod
    def get_best_matching_prompt(
        db: Session, 
        service_key: str, 
        user_level: int, 
        prompt_type: str = "chat"
    ) -> Optional[AIPrompt]:
        """获取最佳匹配的prompt，如果用户等级没有对应prompt，则降级查找"""
        # 首先尝试获取用户等级对应的prompt
        prompt = AIPromptService.get_prompt_by_service_and_level(db, service_key, user_level, prompt_type)
        
        if prompt:
            return prompt
        
        # 如果没有找到，则降级查找（从用户等级向下查找）
        for level in range(user_level - 1, 0, -1):
            prompt = AIPromptService.get_prompt_by_service_and_level(db, service_key, level, prompt_type)
            if prompt:
                return prompt
        
        # 如果还是没有找到，查找默认的1级prompt
        return AIPromptService.get_prompt_by_service_and_level(db, service_key, 1, prompt_type)
    
    @staticmethod
    def get_all_prompts_for_service(
        db: Session, 
        service_key: str, 
        prompt_type: str = "chat"
    ) -> List[AIPrompt]:
        """获取某个服务类型的所有prompt"""
        query = text("""
            SELECT id, service_key, level, prompt_type, system_prompt, user_prompt_template, 
                   is_active, priority, created_at, updated_at
            FROM ai_prompts
            WHERE service_key = :service_key 
              AND prompt_type = :prompt_type
              AND is_active = true
            ORDER BY level ASC, priority DESC
        """)
        result = db.execute(query, {
            "service_key": service_key,
            "prompt_type": prompt_type
        })
        
        prompts = []
        for row in result:
            row_dict = dict(row._mapping)
            prompts.append(AIPrompt(**row_dict))
        
        return prompts
    
    @staticmethod
    def create_prompt(
        db: Session,
        service_key: str,
        level: int,
        prompt_type: str,
        system_prompt: str,
        user_prompt_template: Optional[str] = None,
        priority: int = 0
    ) -> AIPrompt:
        """创建新的prompt"""
        query = text("""
            INSERT INTO ai_prompts (service_key, level, prompt_type, system_prompt, user_prompt_template, priority)
            VALUES (:service_key, :level, :prompt_type, :system_prompt, :user_prompt_template, :priority)
            RETURNING id, service_key, level, prompt_type, system_prompt, user_prompt_template, 
                      is_active, priority, created_at, updated_at
        """)
        result = db.execute(query, {
            "service_key": service_key,
            "level": level,
            "prompt_type": prompt_type,
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template,
            "priority": priority
        })
        db.commit()
        
        row = result.fetchone()
        row_dict = dict(row._mapping)
        return AIPrompt(**row_dict) 