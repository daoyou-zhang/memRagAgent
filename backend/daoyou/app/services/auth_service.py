import dotenv
import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import bcrypt
from fastapi import HTTPException, status
import jwt
from jwt.exceptions import PyJWTError
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.auth_schemas import (
    UserRegister,
    UserLogin,
    UserInfo,
    LoginResponse,
    WechatLogin,
    UnifiedLogin,
    BindWechat,
    UpdateProfileRequest,
    VerifyPhoneRequest,
)
from ..models.user import User
from ..models.wechat_account import WechatAccount
from ..core.database import get_db
from .wechat_service import wechat_service
from .wechat_account_service import wechat_account_service
import unicodedata
import secrets
from redis import Redis

# 配置日志
logger = logging.getLogger(__name__)

# 加载环境变量
dotenv.load_dotenv()

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
# 默认24小时，可通过环境变量覆盖
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# 密码加密函数
def hash_password(password: str) -> str:
    """使用 bcrypt 加密密码"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = {}
    # 将UUID等不可JSON序列化的值统一转换为字符串
    for k, v in data.items():
        try:
            # 简单探测：若是UUID或非基本类型，先转字符串
            if hasattr(v, 'hex') or isinstance(v, (bytes, bytearray)):
                to_encode[k] = str(v)
            else:
                # 再次尝试直接放入
                to_encode[k] = v
        except Exception:
            to_encode[k] = str(v)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class AuthService:
    """认证服务"""
    
    def __init__(self):
        pass
    
    def _sanitize_wechat_nickname(self, nickname: Optional[str]) -> str:
        """清洗微信昵称，避免数据库或显示层出现乱码。
        - 规范化为 NFKC 以合并兼容字符
        - 过滤掉超出 BMP 的字符（常见导致 utf8 非 mb4 存储报错/乱码的 emoji）
        - 去除控制字符
        """
        if not nickname:
            return "微信用户"
        try:
            normalized = unicodedata.normalize('NFKC', str(nickname))
            cleaned_chars = []
            for ch in normalized:
                code = ord(ch)
                # 允许常用可打印字符与基本多文种平面字符，过滤控制符与 >0xFFFF 的字符
                if code < 32:
                    continue
                if code > 0xFFFF:
                    continue
                cleaned_chars.append(ch)
            cleaned = ''.join(cleaned_chars).strip()
            return cleaned or "微信用户"
        except Exception:
            return "微信用户"
    
    def _find_user_by_phone(self, phone: str, db: Session) -> Optional[User]:
        """根据手机号查找用户 - 支持查询两个表"""
        try:
            # 首先在主表中查找
            result = db.query(User).filter(User.phone == phone).first()
            if result:
                return result
            
            # 如果主表中没有找到，检查是否有通过wechat_accounts表关联的用户
            # 这种情况可能发生在用户通过微信登录后绑定手机号的情况
            # 但由于我们的逻辑是删除临时用户，所以这种情况应该很少见
            
            return None
        except Exception as e:
            logger.error(f"查询用户失败: {str(e)}")
            import traceback
            logger.error(f"查询用户详细错误: {traceback.format_exc()}")
            # 返回 None 而不是抛出异常，让上层处理用户不存在的情况
            return None

    def _find_user_by_openid(self, openid: str, db: Session) -> Optional[User]:
        """根据openid查找用户 - 统一使用wechat_accounts表"""
        try:
            # 首先在wechat_accounts表中查找
            wechat_account = db.query(WechatAccount).filter(WechatAccount.openid == openid).first()
            if wechat_account:
                # 通过关联的用户ID查找用户
                return db.query(User).filter(User.id == wechat_account.user_id).first()
            
            # 如果wechat_accounts表中没有，再检查主表（向后兼容）
            return db.query(User).filter(User.openid == openid).first()
        except Exception as e:
            logger.error(f"查询用户失败: {str(e)}")
            return None

    def _find_user_by_unionid(self, unionid: str, db: Session) -> Optional[User]:
        """根据unionid查找用户 - 统一使用wechat_accounts表"""
        try:
            # 首先在wechat_accounts表中查找
            wechat_account = db.query(WechatAccount).filter(WechatAccount.unionid == unionid).first()
            if wechat_account:
                # 通过关联的用户ID查找用户
                return db.query(User).filter(User.id == wechat_account.user_id).first()
            
            # 如果wechat_accounts表中没有，再检查主表（向后兼容）
            return db.query(User).filter(User.unionid == unionid).first()
        except Exception as e:
            logger.error(f"查询用户失败: {str(e)}")
            return None

    def _find_user_by_phone_or_unionid(self, phone: str, unionid: str, db: Session) -> Optional[User]:
        """根据手机号或unionid查找用户（双重检查）"""
        # 优先通过手机号查找
        if phone:
            user = self._find_user_by_phone(phone, db)
            if user:
                return user
        
        # 通过unionid查找
        if unionid:
            user = self._find_user_by_unionid(unionid, db)
            if user:
                return user
        
        return None

    def _check_user_uniqueness(self, phone: str = None, unionid: str = None, openid: str = None, db: Session = None) -> dict:
        """检查用户唯一性，返回冲突信息"""
        conflicts = {}
        
        if phone:
            existing_user = self._find_user_by_phone(phone, db)
            if existing_user:
                conflicts['phone'] = existing_user
        
        if unionid:
            existing_user = self._find_user_by_unionid(unionid, db)
            if existing_user:
                conflicts['unionid'] = existing_user
        
        if openid:
            existing_user = self._find_user_by_openid(openid, db)
            if existing_user:
                conflicts['openid'] = existing_user
        
        return conflicts

    def unified_login(self, login_data: UnifiedLogin, db: Session, redis: Redis = None) -> LoginResponse:
        """统一登录接口 - 支持手机号密码、验证码和微信登录"""
        try:
            if login_data.login_type == "phone":
                if not login_data.phone or not login_data.password:
                    raise HTTPException(status_code=400, detail="手机号和密码不能为空")
                return self._phone_login(login_data.phone, login_data.password, db)
            elif login_data.login_type == "code":
                if not login_data.phone or not login_data.code:
                    raise HTTPException(status_code=400, detail="手机号和验证码不能为空")
                if not redis:
                    raise HTTPException(status_code=500, detail="Redis服务不可用")
                return self._code_login(login_data.phone, login_data.code, db, redis)
            elif login_data.login_type == "wechat":
                if not login_data.code:
                    raise HTTPException(status_code=400, detail="微信授权码不能为空")
                # 使用前端传递的wechat_type，默认为miniprogram
                wechat_type = getattr(login_data, 'wechat_type', 'miniprogram') or 'miniprogram'
                return self._wechat_login(login_data.code, login_data.referrer_id, wechat_type, db)
            else:
                raise HTTPException(status_code=400, detail="不支持的登录类型")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"统一登录失败: {str(e)}")
            import traceback
            raise HTTPException(status_code=500, detail=f"登录失败，请稍后重试。错误信息: {str(e)}")

    def _phone_login(self, phone: str, password: str, db: Session) -> LoginResponse:
        """手机号密码登录"""
        try:

            user = self._find_user_by_phone(phone, db)
            if not user:
                raise HTTPException(status_code=400, detail="用户未注册，请先注册")
            if not user.check_password(password):
                raise HTTPException(status_code=401, detail="密码错误")

            # 生成 JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"sub": str(user.id)},
                expires_delta=access_token_expires
            )

            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            
            try:
                db.commit()
            except Exception as commit_error:
                logger.error(f"数据库提交失败: {str(commit_error)}")
                db.rollback()
                raise HTTPException(status_code=500, detail="登录失败，请稍后重试")
            return LoginResponse(
                success=True,
                message="登录成功",
                token=token,
                user_info=self._user_to_userinfo(user, token),
                is_new_user=False,
                need_bind_phone=False
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"手机号密码登录失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"登录失败，请稍后重试。错误信息: {str(e)}")

    def _code_login(self, phone: str, code: str, db: Session, redis: Redis) -> LoginResponse:
        """验证码登录：若账号不存在则自动创建再登录"""
        try:
            # 验证验证码
            from .sms_service import sms_service
            if not sms_service.verify_code(phone, code, redis):
                raise HTTPException(status_code=400, detail="验证码错误或已过期")
            
            # 查找用户
            user = self._find_user_by_phone(phone, db)
            
            is_new_user = False
            if not user:
                # 自动创建用户（无密码，后续可引导设置）
                user = User(
                    id=str(uuid.uuid4()),
                    phone=phone,
                    name=f"用户{phone[-4:]}",
                    password_hash=hash_password(uuid.uuid4().hex[:8]),
                    openid=None,
                    unionid=None,
                    wechat_nickname=None,
                    wechat_avatar=None,
                    referrer_id=None,
                    is_referrer=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                is_new_user = True
                
            # 生成 JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"sub": str(user.id)},
                expires_delta=access_token_expires
            )
            
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            db.commit()
            
            return LoginResponse(
                success=True,
                message="登录成功" if not is_new_user else "账号已创建并登录",
                token=token,
                user_info=self._user_to_userinfo(user, token),
                is_new_user=is_new_user,
                need_bind_phone=False
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"验证码登录失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"登录失败，请稍后重试。错误信息: {str(e)}")

    def _wechat_login(self, code: str, referrer_id: Optional[str] = None, login_type: str = "miniprogram", db: Session = None) -> LoginResponse:
        """微信登录 - 支持小程序、公众号、网站扫码"""
        try:
            if login_type == "miniprogram":
                return self._miniprogram_login(code, referrer_id, db)
            elif login_type == "mp":
                return self._wechat_oauth_login(code, "mp", referrer_id, db)
            elif login_type == "website":
                return self._wechat_oauth_login(code, "website", referrer_id, db)
            else:
                raise HTTPException(status_code=400, detail="不支持的微信登录类型")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"微信登录失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信登录失败，请稍后重试")

    def _wechat_login_core(self, wechat_data: dict, login_type: str, referrer_id: Optional[str] = None, db: Session = None) -> LoginResponse:
        """微信登录核心逻辑 - 提取公共部分"""
        try:
            openid = wechat_data.get("openid")
            if not openid:
                raise HTTPException(status_code=400, detail="微信授权失败")
            
            # 首先检查users表中是否已存在该openid（避免重复创建）
            existing_user = db.query(User).filter(User.openid == openid).first()
            if existing_user:
                # 更新登录时间
                existing_user.last_login = datetime.utcnow()
                db.commit()
                
                # 生成 JWT token
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                token = create_access_token(
                    data={"sub": existing_user.id},
                    expires_delta=access_token_expires
                )
                
                # 检查是否需要绑定手机号
                need_bind_phone = not existing_user.phone
                return LoginResponse(
                    success=True,
                    message="登录成功" if not need_bind_phone else "请绑定手机号完成注册",
                    token=token,
                    user_info=self._user_to_userinfo(existing_user, token),
                    is_new_user=False,
                    need_bind_phone=need_bind_phone
                )
            
            # 查找是否已有该微信用户（通过wechat_accounts表）
            user = wechat_account_service.find_user_by_wechat_identity(wechat_data, db)
            is_new_user = False
            
            if not user:
                # 新用户，创建临时账号（需要绑定手机号）
                user = self._create_temp_wechat_user(wechat_data, referrer_id, login_type, None, None, db)
                is_new_user = True
            else:
                # 老用户，更新登录时间和微信信息
                user.last_login = datetime.utcnow()
                
                # 更新微信账号关联信息（仅小程序需要）
                if login_type == "miniprogram":
                    wechat_account = db.query(WechatAccount).filter(
                        WechatAccount.user_id == user.id,
                        WechatAccount.openid == openid
                    ).first()
                    
                    if wechat_account:
                        if wechat_data.get("unionid"):
                            wechat_account.unionid = wechat_data["unionid"]
                        wechat_account.updated_at = datetime.utcnow()
                
                db.commit()
            
            # 生成 JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"sub": user.id},
                expires_delta=access_token_expires
            )
            
            # 检查是否需要绑定手机号
            need_bind_phone = not user.phone
            
            response = LoginResponse(
                success=True,
                message="登录成功" if not need_bind_phone else "请绑定手机号完成注册",
                token=token,
                user_info=self._user_to_userinfo(user, token),
                is_new_user=is_new_user,
                need_bind_phone=need_bind_phone
            )
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"微信{login_type}登录核心逻辑失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信登录失败，请稍后重试")

    def _wechat_oauth_login(self, code: str, login_type: str = "mp", referrer_id: Optional[str] = None, db: Session = None) -> LoginResponse:
        """微信OAuth登录 - 支持公众号和开放平台网站扫码"""
        try:
            # 根据登录类型获取不同的access_token
            if login_type == "website":
                # 开放平台网站扫码登录
                wechat_data = wechat_service.get_open_access_token(code)
                login_type_name = "网站扫码"
            else:
                # 微信公众号网页授权登录
                wechat_data = wechat_service.get_access_token(code)
                login_type_name = "公众号"
            
            openid = wechat_data.get("openid")
            access_token = wechat_data.get("access_token")
            
            if not openid:
                raise HTTPException(status_code=400, detail="微信授权失败")
            
            # 获取用户信息（OAuth可以获取）
            user_info = None
            if login_type == "website":
                # 开放平台直接尝试获取用户信息
                try:
                    user_info = wechat_service.get_user_info(access_token, openid)
                except Exception:
                    user_info = None
            else:
                # 公众号根据scope决定是否获取用户信息
                scope = os.getenv('WECHAT_MP_SCOPE', 'snsapi_userinfo')
                if scope == 'snsapi_userinfo':
                    try:
                        user_info = wechat_service.get_user_info(access_token, openid)
                    except Exception:
                        user_info = None
            
            # 如果有用户信息，更新到wechat_data中
            if user_info:
                wechat_data["nickname"] = user_info.get("nickname")
                wechat_data["headimgurl"] = user_info.get("headimgurl")
            
            # 调用核心登录逻辑
            response = self._wechat_login_core(wechat_data, login_type, referrer_id, db)
            
            # 如果是老用户，尝试更新最新昵称头像
            if not response.is_new_user and user_info:
                try:
                    user = db.query(User).filter(User.id == response.user_info.id).first()
                    if user:
                        if user_info.get("nickname"):
                            user.wechat_nickname = self._sanitize_wechat_nickname(user_info["nickname"])
                        if user_info.get("headimgurl"):
                            user.wechat_avatar = user_info["headimgurl"]
                        db.commit()
                except Exception:
                    pass  # 获取用户信息失败不影响登录
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"微信{login_type_name}登录失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信登录失败，请稍后重试")



    def _miniprogram_login(self, code: str, referrer_id: Optional[str] = None, db: Session = None) -> LoginResponse:
        """微信小程序登录"""
        try:

            # 获取小程序session_key和openid
            session_data = wechat_service.get_session_info(code)
            
            openid = session_data.get("openid")
            unionid = session_data.get("unionid")
            session_key = session_data.get("session_key")
            
            if not openid:
                raise HTTPException(status_code=400, detail="微信授权失败")
            
            # 调用核心登录逻辑
            response = self._wechat_login_core(session_data, "miniprogram", referrer_id, db)
            
            return response
            
        except HTTPException:
            logger.error("小程序登录抛出HTTPException")
            raise
        except Exception as e:
            logger.error(f"微信小程序登录失败: {str(e)}")
            import traceback
            logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="微信登录失败，请稍后重试")

    def _create_temp_wechat_user(self, wechat_data: dict, referrer_id: Optional[str], login_type: str, wechat_nickname: Optional[str] = None, wechat_avatar: Optional[str] = None, db: Session = None) -> User:
        """创建临时微信用户（用于绑定手机号）"""
        try:
            if db is None:
                logger.error("db参数为None，无法创建用户")
                raise HTTPException(status_code=500, detail="数据库连接错误")
            
            # 为微信用户生成一个随机密码哈希（避免数据库约束错误）
            import secrets
            import bcrypt
            random_password = secrets.token_urlsafe(16)  # 生成16字节的随机密码
            salt = bcrypt.gensalt()
            default_password_hash = bcrypt.hashpw(random_password.encode('utf-8'), salt).decode('utf-8')
            
            # 确保referrer_id是字符串类型，避免UUID序列化错误
            referrer_id_str = str(referrer_id) if referrer_id else None
            
            # 创建用户，设置主要的微信信息
            new_user = User(
                id=str(uuid.uuid4()),
                name="微信用户",
                phone=None,
                password_hash=default_password_hash,  # 设置默认密码哈希
                openid=wechat_data.get("openid"),  # 设置主要openid
                unionid=wechat_data.get("unionid"),  # 设置主要unionid
                wechat_nickname=wechat_data.get("nickname") or "微信用户",  # 设置主要昵称
                wechat_avatar=wechat_data.get("headimgurl") or "",  # 设置主要头像
                referrer_id=referrer_id_str,  # 使用字符串类型
                is_referrer=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # 创建微信账号关联（从表）
            wechat_account_service.create_wechat_account(
                user_id=str(new_user.id),
                openid=wechat_data.get("openid"),
                wechat_type=login_type,
                unionid=wechat_data.get("unionid"),
                wechat_nickname=wechat_data.get("nickname") or "微信用户",
                wechat_avatar=wechat_data.get("headimgurl") or "",
                db=db
            )
            
            return new_user
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建临时微信用户失败: {str(e)}")
            raise
    
    def _user_to_userinfo(self, user: User, token: str, binding_status: Optional[dict] = None) -> UserInfo:
        """将用户对象转换为UserInfo对象"""
        user_info = UserInfo(
            id=user.id,
            phone=user.phone,
            username=user.name or "",
            password="",
            openid=user.openid,
            unionid=user.unionid,
            wechat_nickname=user.wechat_nickname,
            wechat_avatar=user.wechat_avatar,
            referrer_id=user.referrer_id,
            is_referrer=user.is_referrer or False,
            token=token,
            last_login=user.last_login
        )
        
        # 如果有绑定状态，添加到用户信息中
        if binding_status:
            user_info.binding_status = binding_status
            
        return user_info

    def bind_phone(self, user_id: str, phone: str, password: str, db: Session) -> dict:
        """绑定手机号到微信账号 - 新的主从逻辑"""
        try:
            # 查找当前用户（可能是临时微信账号）
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 若未提供密码（短信绑定模式），生成随机密码
            gen_password = None
            if not password:
                import secrets
                gen_password = secrets.token_urlsafe(10)
                password = gen_password

            # 检查手机号是否已被其他用户使用
            existing_user = self._find_user_by_phone(phone, db)

            # 分支A：手机号从未被使用 → 直接绑定到当前用户
            if not existing_user:
                if current_user.phone:
                    raise HTTPException(status_code=400, detail="用户已绑定手机号")
                current_user.phone = phone
                current_user.set_password(password)
                current_user.name = current_user.name or "微信用户"
                current_user.updated_at = datetime.utcnow()
                db.commit()
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                new_token = create_access_token(data={"sub": str(current_user.id)}, expires_delta=access_token_expires)
                return {
                    "success": True,
                    "message": "手机号绑定成功" + ("（已为您生成默认密码）" if gen_password else ""),
                    "token": new_token,
                    "data": self._user_to_userinfo(current_user, new_token)
                }

            # 分支B：手机号已被其他用户使用 → 在附表创建关联，不删除临时用户
            if existing_user.id != current_user.id:
                try:
                    # 获取当前用户的微信账号信息
                    current_wechat_accounts = db.query(WechatAccount).filter(
                        WechatAccount.user_id == current_user.id
                    ).all()
                    
                    if not current_wechat_accounts:
                        raise HTTPException(status_code=400, detail="当前用户没有微信账号信息")
                    
                    # 将微信账号关联到已存在的用户（在附表创建）
                    for wechat_account in current_wechat_accounts:
                        # 检查是否已有相同的openid关联
                        existing_account = db.query(WechatAccount).filter(
                            WechatAccount.openid == wechat_account.openid
                        ).first()
                        
                        if existing_account:
                            # 如果已有相同openid，更新关联到已存在的用户
                            existing_account.user_id = existing_user.id
                            existing_account.updated_at = datetime.utcnow()
                        else:
                            # 创建新的关联到已存在的用户
                            wechat_account_service.link_wechat_to_existing_user(
                                openid=wechat_account.openid,
                                wechat_type=wechat_account.wechat_type,
                                existing_user_id=str(existing_user.id),
                                unionid=wechat_account.unionid,
                                wechat_nickname=wechat_account.wechat_nickname,
                                wechat_avatar=wechat_account.wechat_avatar,
                                db=db
                            )
                    
                    # 更新主用户表的微信信息（如果主用户没有的话）
                    if not existing_user.openid and current_user.openid:
                        existing_user.openid = current_user.openid
                    if not existing_user.unionid and current_user.unionid:
                        existing_user.unionid = current_user.unionid
                    if not existing_user.wechat_nickname and current_user.wechat_nickname:
                        existing_user.wechat_nickname = current_user.wechat_nickname
                    if not existing_user.wechat_avatar and current_user.wechat_avatar:
                        existing_user.wechat_avatar = current_user.wechat_avatar
                    
                    existing_user.updated_at = datetime.utcnow()
                    
                    # 重要：删除临时用户，因为已经关联到主用户
                    db.delete(current_user)
                    db.commit()
                    
                    # 生成新token（使用已存在用户的token）
                    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                    new_token = create_access_token(data={"sub": str(existing_user.id)}, expires_delta=access_token_expires)
                    
                    return {
                        "success": True,
                        "message": "账号关联成功，已绑定到现有账号",
                        "token": new_token,
                        "data": self._user_to_userinfo(existing_user, new_token)
                    }
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"关联微信账号失败: {str(e)}")
                    raise HTTPException(status_code=500, detail="账号关联失败，请稍后重试")
            
            # 如果手机号已被当前用户使用
            return {
                "success": False,
                "message": "该手机号已被当前用户绑定"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"绑定手机号失败: {str(e)}")
            raise HTTPException(status_code=500, detail="绑定失败，请稍后重试")

    def bind_wechat(self, bind_data: BindWechat, db: Session) -> LoginResponse:
        """绑定微信到现有手机号账号 - 新的主从逻辑"""
        try:
            # 验证手机号密码
            user = self._find_user_by_phone(bind_data.phone, db)
            if not user:
                raise HTTPException(status_code=401, detail="用户不存在或密码错误")
                
            if not user.check_password(bind_data.password):
                raise HTTPException(status_code=401, detail="用户不存在或密码错误")
            
            # 获取微信信息
            wechat_data = wechat_service.get_access_token(bind_data.code)
            openid = wechat_data.get("openid")
            unionid = wechat_data.get("unionid")
            
            if not openid:
                raise HTTPException(status_code=400, detail="微信授权失败")
            
            # 检查该微信是否已被其他账号绑定（通过附表检查）
            existing_wechat_account = db.query(WechatAccount).filter(
                WechatAccount.openid == openid
            ).first()
            
            if existing_wechat_account and existing_wechat_account.user_id != user.id:
                raise HTTPException(status_code=400, detail="该微信账号已被其他用户绑定")
            
            # 检查unionid冲突（通过附表检查）
            if unionid:
                existing_unionid_account = db.query(WechatAccount).filter(
                    WechatAccount.unionid == unionid
                ).first()
                
                if existing_unionid_account and existing_unionid_account.user_id != user.id:
                    raise HTTPException(status_code=400, detail="该微信账号已被其他用户绑定")
            
            # 获取微信用户信息
            user_info = wechat_service.get_user_info(wechat_data.get("access_token"), openid)
            
            # 在附表创建微信账号关联（不更新主表）
            wechat_account_service.create_wechat_account(
                user_id=str(user.id),
                openid=openid,
                unionid=unionid,
                wechat_type="website",  # Web端绑定
                wechat_nickname=user_info.get("nickname"),
                wechat_avatar=user_info.get("headimgurl"),
                db=db
            )
            
            # 更新主用户表的微信信息（如果主用户没有的话）
            if not user.openid:
                user.openid = openid
            if not user.unionid:
                user.unionid = unionid
            if not user.wechat_nickname:
                user.wechat_nickname = user_info.get("nickname")
            if not user.wechat_avatar:
                user.wechat_avatar = user_info.get("headimgurl")
            
            user.updated_at = datetime.utcnow()
            db.commit()
            
            # 生成新的token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"sub": user.id},
                expires_delta=access_token_expires
            )
            
            return LoginResponse(
                success=True,
                message="微信绑定成功",
                token=token,
                user_info=self._user_to_userinfo(user, token),
                is_new_user=False,
                need_bind_phone=False
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"绑定微信失败: {str(e)}")
            raise HTTPException(status_code=500, detail="绑定失败，请稍后重试")

    def register(self, user_data: UserRegister, db: Session, redis: Redis) -> LoginResponse:
        """用户注册"""
        try:
            # 校验短信验证码
            redis_code = redis.get(f"sms_code:{user_data.phone}")
            if not redis_code or user_data.code != redis_code:
                logger.warning(f"注册失败：验证码错误或已过期，手机号 {user_data.phone}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="验证码错误或已过期"
                )
            # 检查手机号是否已注册
            existing_user = self._find_user_by_phone(user_data.phone, db)
            if existing_user:
                logger.warning(f"注册失败：手机号 {user_data.phone} 已被注册")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="手机号已被注册"
                )

            # 检查两次密码是否一致
            if user_data.password != user_data.confirmPassword:
                logger.warning("注册失败：两次输入的密码不一致")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="两次输入的密码不一致"
                )

            # 创建新用户
            new_user = User(
                id=str(uuid.uuid4()),
                phone=user_data.phone,
                name=user_data.name,
                password_hash=hash_password(user_data.password),
                openid=None,
                unionid=None,
                wechat_nickname=None,
                wechat_avatar=None,
                referrer_id=user_data.referrer_id,
                is_referrer=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # 生成 JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"sub": str(new_user.id)},
                expires_delta=access_token_expires
            )
            
            return LoginResponse(
                success=True,
                message="注册成功",
                token=token,
                user_info=self._user_to_userinfo(new_user, token),
                is_new_user=True,
                need_bind_phone=False
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="注册失败，请稍后重试"
            )

    def login(self, login_data: UserLogin, db: Session) -> LoginResponse:
        """用户登录 - 保持向后兼容"""
        return self._phone_login(login_data.phone, login_data.password, db)

    def get_user_by_token(self, token: str, include_binding_status: bool = False, db_session: Session = None) -> Optional[UserInfo]:
        """根据 token 获取用户信息 - 支持查询两个表"""
        try:
            # 验证 JWT token
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id: str = payload.get("sub")
                if user_id is None:
                    return None
            except PyJWTError:
                return None

            # 使用数据库会话获取用户
            db = db_session or next(get_db())
            should_close_db = db_session is None
            
            try:
                # 从主表查询用户
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"获取用户信息失败：无效的 token")
                    return None
                
                # 如果需要绑定状态，同时查询
                if include_binding_status:
                    # 查询微信账号关联
                    wechat_accounts = db.query(WechatAccount).filter(
                        WechatAccount.user_id == user_id
                    ).all()
                    
                    # 检查是否有微信绑定（主表或附表）
                    has_wechat_main = bool(user.openid or user.unionid)
                    has_wechat_accounts = len(wechat_accounts) > 0
                    has_wechat = has_wechat_main or has_wechat_accounts
                    
                    # 检查手机号绑定
                    has_phone = bool(user.phone)
                    need_bind_phone = not has_phone
                    
                    # 创建绑定状态
                    binding_status = {
                        "has_phone": has_phone,
                        "has_wechat": has_wechat,
                        "need_bind_phone": need_bind_phone,
                        "wechat_accounts": [
                            {
                                "openid": wa.openid,
                                "unionid": wa.unionid,
                                "wechat_type": wa.wechat_type,
                                "wechat_nickname": wa.wechat_nickname
                            }
                            for wa in wechat_accounts
                        ],
                        "main_wechat": {
                            "openid": user.openid,
                            "unionid": user.unionid,
                            "wechat_nickname": user.wechat_nickname
                        } if has_wechat_main else None
                    }
                    
                    # 创建包含绑定状态的用户信息
                    return self._user_to_userinfo(user, token, binding_status)
                else:
                    logger.debug(f"成功获取用户信息: {user.phone or user.openid or 'unknown'}")
                    return self._user_to_userinfo(user, token)
            finally:
                if should_close_db:
                    db.close()
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取用户信息失败"
            )

    def get_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """根据用户ID获取用户信息"""
        try:
            # 使用数据库会话获取用户
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"获取用户信息失败：无效的用户ID {user_id}")
                    return None
                    
                logger.debug(f"成功获取用户信息: {user.phone or user.openid or 'unknown'}")
                return self._user_to_userinfo(user, "")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取用户信息失败"
            )

    def get_user_by_id_or_phone(self, value: str) -> Optional[UserInfo]:
        """根据用户ID或手机号获取用户信息"""
        try:
            db = next(get_db())
            try:
                user = db.query(User).filter((User.id == value) | (User.phone == value)).first()
                if not user:
                    logger.warning(f"获取用户信息失败：无效的用户ID或手机号 {value}")
                    return None
                logger.debug(f"成功获取用户信息: {user.phone or user.openid or 'unknown'}")
                return self._user_to_userinfo(user, "")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取用户信息失败"
            )

    def update_profile(self, user_id: str, update_data: UpdateProfileRequest, db: Session) -> dict:
        """更新用户信息"""
        try:
            # 查找用户
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 验证手机号是否已被其他用户使用
            if update_data.phone and update_data.phone != user.phone:
                existing_user = self._find_user_by_phone(update_data.phone, db)
                if existing_user and existing_user.id != user_id:
                    raise HTTPException(status_code=400, detail="手机号已被其他用户使用")
            
            # 验证密码
            if update_data.password:
                if not update_data.confirmPassword:
                    raise HTTPException(status_code=400, detail="请确认新密码")
                if update_data.password != update_data.confirmPassword:
                    raise HTTPException(status_code=400, detail="两次输入的密码不一致")
            
            # 更新用户信息
            if update_data.username:
                user.name = update_data.username
            if update_data.phone:
                user.phone = update_data.phone
            if update_data.password:
                user.set_password(update_data.password)
            
            user.updated_at = datetime.utcnow()
            
            # 保存更新
            db.commit()
            
            return {
                "success": True,
                "message": "用户信息更新成功",
                "data": self._user_to_userinfo(user, "")
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新用户信息失败: {str(e)}")
            raise HTTPException(status_code=500, detail="更新失败，请稍后重试")

    def verify_phone(self, phone: str, db: Session) -> dict:
        """验证手机号是否存在"""
        try:
            user = self._find_user_by_phone(phone, db)
            
            if not user:
                return {
                    "success": False,
                    "message": "手机号不存在",
                    "data": None
                }
            
            return {
                "success": True,
                "message": "手机号验证成功",
                "data": {
                    "user_id": user.id,
                    "username": user.name or "",
                    "phone": user.phone or ""
                }
            }
            
        except Exception as e:
            logger.error(f"验证手机号失败: {str(e)}")
            raise HTTPException(status_code=500, detail="验证失败，请稍后重试")

    def get_user_binding_status(self, user_id: str, db: Session) -> dict:
        """获取用户的绑定状态 - 查询两个表"""
        try:
            # 查询主表用户信息
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "has_phone": False,
                    "has_wechat": False,
                    "wechat_accounts": [],
                    "need_bind_phone": True
                }
            
            # 查询微信账号关联
            wechat_accounts = db.query(WechatAccount).filter(
                WechatAccount.user_id == user_id
            ).all()
            
            # 检查是否有微信绑定（主表或附表）
            has_wechat_main = bool(user.openid or user.unionid)
            has_wechat_accounts = len(wechat_accounts) > 0
            has_wechat = has_wechat_main or has_wechat_accounts
            
            # 检查手机号绑定
            has_phone = bool(user.phone)
            
            # 判断是否需要绑定手机号
            need_bind_phone = not has_phone
            
            return {
                "has_phone": has_phone,
                "has_wechat": has_wechat,
                "need_bind_phone": need_bind_phone,
                "wechat_accounts": [
                    {
                        "openid": wa.openid,
                        "unionid": wa.unionid,
                        "wechat_type": wa.wechat_type,
                        "wechat_nickname": wa.wechat_nickname
                    }
                    for wa in wechat_accounts
                ],
                "main_wechat": {
                    "openid": user.openid,
                    "unionid": user.unionid,
                    "wechat_nickname": user.wechat_nickname
                } if has_wechat_main else None
            }
            
        except Exception as e:
            logger.error(f"获取用户绑定状态失败: {str(e)}")
            return {
                "has_phone": False,
                "has_wechat": False,
                "need_bind_phone": True,
                "wechat_accounts": []
            }

# 创建 AuthService 实例
user_service = AuthService() 