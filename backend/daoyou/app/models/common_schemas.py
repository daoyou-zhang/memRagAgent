from pydantic import BaseModel, Field
from datetime import datetime

class TestResponse(BaseModel):
    """测试接口响应模型"""
    status: str = Field(..., example="healthy")
    message: str = Field(..., example="服务运行正常")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        example="2023-07-20T15:30:45.123456"
    ) 