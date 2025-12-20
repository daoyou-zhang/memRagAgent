from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class UserLogin(BaseModel):
    """用户登录请求模型"""
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")
    password: str = Field(..., min_length=6, max_length=20, description="密码")

class CodeLogin(BaseModel):
    """验证码登录请求模型 - 专门用于短信验证码登录"""
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="短信验证码（6位数字）")

class SendSmsRequest(BaseModel):
    """发送短信验证码请求模型 - 专门用于短信验证码"""
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")
    type: str = Field(..., description="验证码类型: 'register' 或 'login'")

class WechatLogin(BaseModel):
    """微信登录请求模型"""
    code: str = Field(..., description="微信授权码")
    referrer_id: Optional[UUID] = Field(None, description="推荐者ID")

class UnifiedLogin(BaseModel):
    """统一登录请求模型 - 支持手机号密码、验证码和微信登录"""
    login_type: str = Field(..., description="登录类型: 'phone' 或 'code' 或 'wechat'")
    phone: Optional[str] = Field(None, pattern="^1[3-9]\\d{9}$", description="手机号")
    password: Optional[str] = Field(None, min_length=6, max_length=20, description="密码")
    code: Optional[str] = Field(None, description="验证码或微信授权码")  # 移除长度限制
    referrer_id: Optional[UUID] = Field(None, description="推荐者ID")
    wechat_type: Optional[str] = Field(None, description="微信登录类型: 'miniprogram' 或 'mp'")

class BindWechat(BaseModel):
    """绑定微信请求模型"""
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")
    password: str = Field(..., min_length=6, max_length=20, description="密码")
    code: str = Field(..., description="微信授权码")

class UserRegister(BaseModel):
    """用户注册请求模型"""
    name: str = Field(..., min_length=2, max_length=20, description="用户名")
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")
    password: str = Field(..., min_length=6, max_length=20, description="密码")
    confirmPassword: str = Field(..., min_length=6, max_length=20, description="确认密码")
    code: str = Field(..., min_length=6, max_length=6, description="短信验证码")
    referrer_id: Optional[UUID] = Field(None, description="推荐者ID")

class UpdateProfileRequest(BaseModel):
    """更新用户信息请求模型"""
    username: Optional[str] = Field(None, min_length=2, max_length=20, description="用户名")
    phone: Optional[str] = Field(None, pattern="^1[3-9]\\d{9}$", description="手机号")
    password: Optional[str] = Field(None, min_length=6, max_length=20, description="新密码")
    confirmPassword: Optional[str] = Field(None, min_length=6, max_length=20, description="确认新密码")

class VerifyPhoneRequest(BaseModel):
    """验证手机号请求模型"""
    phone: str = Field(..., pattern="^1[3-9]\\d{9}$", description="手机号")

class WechatAccountInfo(BaseModel):
    """微信账号信息"""
    openid: Optional[str] = None
    unionid: Optional[str] = None
    wechat_type: Optional[str] = None
    wechat_nickname: Optional[str] = None

class MainWechatInfo(BaseModel):
    """主表微信信息"""
    openid: Optional[str] = None
    unionid: Optional[str] = None
    wechat_nickname: Optional[str] = None

class BindingStatus(BaseModel):
    """绑定状态"""
    has_phone: bool = False
    has_wechat: bool = False
    need_bind_phone: bool = True
    wechat_accounts: List[WechatAccountInfo] = []
    main_wechat: Optional[MainWechatInfo] = None

class UserInfo(BaseModel):
    """用户信息模型"""
    id: UUID
    phone: Optional[str] = None
    username: str
    password: str  # 实际存储时应该是加密后的密码
    openid: Optional[str] = None
    unionid: Optional[str] = None
    wechat_nickname: Optional[str] = None
    wechat_avatar: Optional[str] = None
    referrer_id: Optional[UUID] = None
    is_referrer: bool = False
    token: Optional[str] = None
    last_login: Optional[datetime] = None
    binding_status: Optional[BindingStatus] = None

class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str
    token: Optional[str] = None
    user_info: Optional[UserInfo] = None
    is_new_user: bool = False  # 是否为新用户
    need_bind_phone: bool = False  # 是否需要绑定手机号 