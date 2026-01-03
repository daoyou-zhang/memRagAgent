"""聊天相关数据模型"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色：user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    audio_url: Optional[str] = Field(None, description="语音 URL（如果有）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class VoiceMessage(BaseModel):
    """语音消息"""
    audio_data: bytes = Field(..., description="音频数据（base64 或二进制）")
    format: str = Field("pcm", description="音频格式：pcm/wav/mp3")
    sample_rate: int = Field(16000, description="采样率")
    channels: int = Field(1, description="声道数")


class ChatSession(BaseModel):
    """聊天会话"""
    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    project_id: Optional[str] = Field(None, description="项目 ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息历史")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")


class ChatRequest(BaseModel):
    """聊天请求"""
    input: str = Field(..., description="用户输入")
    user_id: str = Field(..., description="用户 ID")
    session_id: Optional[str] = Field(None, description="会话 ID")
    project_id: Optional[str] = Field(None, description="项目 ID")
    enable_voice: bool = Field(False, description="是否返回语音")
    enable_digital_human: bool = Field(False, description="是否返回数字人视频")
    voice_config: Optional[Dict[str, Any]] = Field(None, description="语音配置")


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str = Field(..., description="回复内容")
    session_id: str = Field(..., description="会话 ID")
    audio_url: Optional[str] = Field(None, description="语音 URL")
    video_url: Optional[str] = Field(None, description="数字人视频 URL")
    processing_time: float = Field(..., description="处理时间（秒）")
