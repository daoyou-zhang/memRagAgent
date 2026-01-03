"""数字人 API

3D 数字人视频生成接口
"""
from fastapi import APIRouter, HTTPException
from loguru import logger

from ..models.digital_human import DigitalHumanRequest, DigitalHumanResponse
from ..services import get_digital_human_service


router = APIRouter()


@router.post("/generate", response_model=DigitalHumanResponse)
async def generate_digital_human(request: DigitalHumanRequest):
    """生成数字人视频
    
    根据文本生成带有 3D 数字人的视频
    """
    try:
        dh_service = get_digital_human_service()
        
        result = await dh_service.generate_video(
            text=request.text,
            config=request.config,
        )
        
        return DigitalHumanResponse(
            video_url=result.get("video_url"),
            duration=result.get("duration", 0.0),
            frame_count=result.get("frame_count"),
            metadata=result.get("metadata"),
        )
    
    except Exception as exc:
        logger.error(f"数字人生成失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/models")
async def list_models():
    """列出可用的数字人模型"""
    # TODO: 从阿里云获取可用模型列表
    return {
        "models": [
            {
                "id": "default",
                "name": "默认数字人",
                "description": "通用数字人模型",
            }
        ]
    }


@router.get("/voices")
async def list_voices():
    """列出可用的语音角色"""
    return {
        "voices": [
            {"id": "xiaoyun", "name": "小云", "gender": "female", "language": "zh"},
            {"id": "xiaogang", "name": "小刚", "gender": "male", "language": "zh"},
            {"id": "ruoxi", "name": "若曦", "gender": "female", "language": "zh"},
        ]
    }
