from typing import Optional

from pydantic import BaseModel


class BaseChatRequest(BaseModel):
    """基础聊天请求模型，用于 daoyou 内部聊天路由。

    - type: 服务类型 / agent 标识，例如 gui_water、geng_metal 等
    - query: 用户输入的问题文本
    - key: 会话 key（可选），用于复用或恢复会话
    """

    type: Optional[str] = None
    query: str
    key: Optional[str] = None
