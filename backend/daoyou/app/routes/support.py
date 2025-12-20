from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import logging

from ..core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


class ContactMessage(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=5, max_length=20)
    email: EmailStr | None = None
    subject: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=1000)


@router.post("/contact")
def submit_contact_message(data: ContactMessage, db: Session = Depends(get_db)):
    try:
        # 目前先写入日志，后续可接入数据库或飞书/企微Webhook
        logger.info(
            "CONTACT_MESSAGE name=%s phone=%s email=%s subject=%s message=%s",
            data.name,
            data.phone,
            data.email or "",
            data.subject,
            data.message[:500]
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


