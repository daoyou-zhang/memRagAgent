"""数字人相关数据模型"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DigitalHumanConfig(BaseModel):
    """数字人配置"""
    model_id: str = Field("default", description="数字人模型 ID")
    voice: str = Field("xiaoyun", description="语音角色")
    background: str = Field("office", description="背景场景")
    expression: str = Field("neutral", description="表情：neutral/happy/sad/angry")
    pose: str = Field("standing", description="姿势：standing/sitting")
    camera_angle: str = Field("front", description="镜头角度：front/side/close")


class DigitalHumanFrame(BaseModel):
    """数字人视频帧"""
    frame_data: bytes = Field(..., description="帧数据")
    timestamp: float = Field(..., description="时间戳")
    format: str = Field("jpeg", description="格式：jpeg/png")


class DigitalHumanRequest(BaseModel):
    """数字人生成请求"""
    text: str = Field(..., description="要说的文本")
    config: Optional[DigitalHumanConfig] = Field(None, description="数字人配置")
    output_format: str = Field("mp4", description="输出格式：mp4/webm/frames")


class DigitalHumanResponse(BaseModel):
    """数字人生成响应"""
    video_url: Optional[str] = Field(None, description="视频 URL")
    duration: float = Field(..., description="视频时长（秒）")
    frame_count: Optional[int] = Field(None, description="帧数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
