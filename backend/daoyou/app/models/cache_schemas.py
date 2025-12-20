from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class CacheFileListResponse(BaseModel):
    data: Dict[str, List[str]] = Field(..., description="缓存文件名列表")

class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user/ai")
    text: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(None, description="消息时间")

class CacheFileDetailResponse(BaseModel):
    key: str = Field(..., description="缓存主键")
    data: Any = Field(..., description="缓存内容，result为BaziResponse，chatcache为聊天消息列表")
