from fastapi import APIRouter, HTTPException, Depends, Request, Body, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..services.auth_service import AuthService, create_access_token
from ..core.database import get_db
from ..models.auth_schemas import (
    UserRegister,
    UserLogin,
    CodeLogin,
    SendSmsRequest,
    UserInfo,
    LoginResponse,
    UnifiedLogin,
    BindWechat,
    UpdateProfileRequest,
    VerifyPhoneRequest,
)

import re
import uuid
import time
import logging
from typing import Dict, Optional
import os
import random
import re
from redis import Redis
from ..services.rate_limit_service import rate_limit_service
from ..services.sms_service import sms_service
from urllib.parse import quote_plus
import json
from ..models.user import User
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
security = HTTPBearer()
user_service = AuthService()

QR_KEY_PREFIX = "qr:"
QR_TTL_SECONDS = 300  # 5分钟有效期

@router.post("/wechat-qr-code")
async def generate_wechat_qr_code():
    """生成微信登录二维码"""
    try:
        # 生成唯一的二维码ID
        qr_code_id = str(uuid.uuid4())
        base_url = os.getenv("BASE_URL", "https://api.zdaoyou.chat")
        callback_path = "/api/auth/wechat-callback"
        redirect_uri = quote_plus(f"{base_url}{callback_path}")

        # 记录 Redis 连接指纹
        try:
            info = rate_limit_service.redis.info(section='server')
        except Exception as e:
            logger.warning(f"[QR] 无法获取Redis信息: {str(e)}")

        # 优先尝试开放平台网站应用
        open_app_id = os.getenv("WECHAT_OPEN_APP_ID")
        scope = "snsapi_login"
        qr_code_url = None
        if open_app_id:
            qr_code_url = (
                f"https://open.weixin.qq.com/connect/qrconnect?appid={open_app_id}"
                f"&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={qr_code_id}#wechat_redirect"
            )
            qr_data = {
                "status": "waiting",
                "created_at": time.time(),
                "qr_code_url": qr_code_url,
            }
            rate_limit_service.redis.setex(f"{QR_KEY_PREFIX}{qr_code_id}", QR_TTL_SECONDS, json.dumps(qr_data))
            # 打印TTL
            try:
                ttl = rate_limit_service.redis.ttl(f"{QR_KEY_PREFIX}{qr_code_id}")
            except Exception:
                pass
        else:
            # 回退到公众号网页授权
            mp_app_id = os.getenv("WECHAT_MP_APP_ID")
            if not mp_app_id:
                # 如果没有配置，使用模拟二维码（同样写入Redis便于查询）
                qr_data = {
                    "status": "waiting",
                    "created_at": time.time(),
                    "qr_code_url": f"mock://wechat-login?state={qr_code_id}"
                }
                rate_limit_service.redis.setex(f"{QR_KEY_PREFIX}{qr_code_id}", QR_TTL_SECONDS, json.dumps(qr_data))
                try:
                    ttl = rate_limit_service.redis.ttl(f"{QR_KEY_PREFIX}{qr_code_id}")
                except Exception:
                    pass
            else:
                scope = os.getenv('WECHAT_MP_SCOPE', 'snsapi_userinfo')
                qr_code_url = (
                    f"https://open.weixin.qq.com/connect/oauth2/authorize?appid={mp_app_id}"
                    f"&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={qr_code_id}#wechat_redirect"
                )
                qr_data = {
                    "status": "waiting",
                    "created_at": time.time(),
                    "qr_code_url": qr_code_url
                }
                rate_limit_service.redis.setex(f"{QR_KEY_PREFIX}{qr_code_id}", QR_TTL_SECONDS, json.dumps(qr_data))
                try:
                    ttl = rate_limit_service.redis.ttl(f"{QR_KEY_PREFIX}{qr_code_id}")
                except Exception:
                    pass
        
        stored = rate_limit_service.redis.get(f"{QR_KEY_PREFIX}{qr_code_id}")
        qr_resp = json.loads(stored) if stored else {"qr_code_url": None}
        
        # 返回给前端用于 wxLogin.js 的必要参数（若已配置开放平台）
        resp_data = {
            "qr_code_id": qr_code_id,
            "qr_code_url": qr_resp.get("qr_code_url"),
        }
        if open_app_id:
            resp_data.update({
                "appid": open_app_id,
                "redirect_uri": f"{base_url}{callback_path}",  # 未编码版本，前端自行encode
                "scope": "snsapi_login",
                "method": "wx_js"
            })
        return {
            "success": True,
            "data": resp_data
        }
    except Exception as e:
        logger.error(f"生成二维码失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成二维码失败")



@router.get("/wechat-callback")
async def wechat_callback(code: str, state: str, db: Session = Depends(get_db)):
    """微信扫码登录回调：优先根据 unionid/openid 直接登录；否则创建临时用户并跳转绑定手机号"""
    try:
        # 校验 state 并刷新二维码状态
        data = rate_limit_service.redis.get(f"{QR_KEY_PREFIX}{state}")
        if not data:
            raise HTTPException(status_code=400, detail="无效的二维码状态")
        qr_data = json.loads(data)
        qr_data["status"] = "scanned"
        qr_data["code"] = code
        qr_data["updated_at"] = time.time()
        rate_limit_service.redis.setex(f"{QR_KEY_PREFIX}{state}", QR_TTL_SECONDS, json.dumps(qr_data))

        front_base = os.getenv("FRONT_BASE_URL", "https://www.zdaoyou.chat")
        # 走统一登录流程（网站扫码），生成完整登录态
        login_resp = user_service._wechat_oauth_login(code, "website", None, db)
        
        if not login_resp or not login_resp.token:
            logger.error("微信回调登录失败：login_resp或token为空")
            raise HTTPException(status_code=500, detail="微信登录失败，请稍后重试")
        
        target = f"{front_base}/bind-phone?token={login_resp.token}" if login_resp.need_bind_phone else f"{front_base}/?token={login_resp.token}"
        
        # 返回302重定向
        return RedirectResponse(url=target, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"微信回调处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="微信回调处理失败")


@router.post("/register", response_model=LoginResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        return user_service.register(user_data, db, rate_limit_service.redis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

@router.post("/login", response_model=LoginResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录 - 保持向后兼容"""
    try:
        return user_service.login(login_data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")

@router.post("/code-login", response_model=LoginResponse)
async def code_login(login_data: CodeLogin, db: Session = Depends(get_db)):
    """验证码登录"""
    try:
        return user_service._code_login(login_data.phone, login_data.code, db, rate_limit_service.redis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")

@router.post("/unified-login", response_model=LoginResponse)
async def unified_login(login_data: UnifiedLogin, db: Session = Depends(get_db)):
    """统一登录接口 - 支持手机号密码、验证码和微信登录"""
    try:
        return user_service.unified_login(login_data, db, rate_limit_service.redis)
    except HTTPException:
        # 重新抛出 HTTPException，保持原始状态码和错误信息
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"统一登录路由异常: {str(e)}")
        import traceback
        logger.error(f"统一登录路由异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"统一登录失败: {str(e)}")
@router.post("/bind-wechat", response_model=LoginResponse)
async def bind_wechat(bind_data: BindWechat, db: Session = Depends(get_db)):
    """绑定微信到现有手机号账号"""
    try:
        return user_service.bind_wechat(bind_data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="绑定失败，请稍后重试")

@router.post("/bind-phone")
async def bind_phone(
    request: Request,
    bind_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """绑定手机号到微信账号"""
    try:
        # 获取token：优先Authorization，其次查询参数token，最后body.token
        auth_header = request.headers.get("Authorization")
        token = None
        token_source = "none"
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            token_source = "header"
        if not token:
            qp = request.query_params.get("token")
            if qp:
                token = qp
                token_source = "query"
        if not token:
            bp = bind_data.get("token")
            if bp:
                token = bp
                token_source = "body"
        if not token:
            logger.warning("bind_phone 缺少token")
            raise HTTPException(status_code=401, detail="未提供有效的认证token")
        
        user_info = user_service.get_user_by_token(token)
        if not user_info:
            logger.warning("bind_phone token无效或用户不存在")
            raise HTTPException(status_code=401, detail="无效的认证token")
        # 验证请求数据
        phone = bind_data.get("phone")
        password = bind_data.get("password")
        code = bind_data.get("code")
        
        if not phone:
            raise HTTPException(status_code=400, detail="手机号不能为空")
        if not re.match(r"^1[3-9]\d{9}$", phone):
            raise HTTPException(status_code=400, detail="手机号格式不正确")
        
        # 验证策略：如果没有提供密码，则必须提供验证码
        if not password and not code:
            raise HTTPException(status_code=400, detail="缺少密码或验证码")
        if password and len(password) < 6:
            raise HTTPException(status_code=400, detail="密码至少6位")

        # 如提供验证码则校验
        if code:
            from ..services.sms_service import sms_service as _sms
            if not _sms.verify_code(phone, code, rate_limit_service.redis):
                raise HTTPException(status_code=400, detail="验证码错误或已过期")
        
        # 绑定手机号（内部会处理合并与随机密码）
        result = user_service.bind_phone(user_info.id, phone, password or "", db)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"bind_phone 失败: {str(e)}")
        raise HTTPException(status_code=500, detail="绑定失败，请稍后重试")

@router.post("/send-sms-code")
async def send_sms_code(sms_data: SendSmsRequest):
    """发送短信验证码"""
    try:
        # 验证手机号格式
        if not re.match(r"^1[3-9]\d{9}$", sms_data.phone):
            raise HTTPException(status_code=400, detail="手机号格式不正确")
        
        # 验证验证码类型
        if sms_data.type not in ["register", "login"]:
            raise HTTPException(status_code=400, detail="验证码类型不正确")
        
        # 发送验证码
        result = await sms_service.send_verification_code(sms_data.phone, rate_limit_service.redis)
        
        if result["success"]:
            return {"success": True, "message": "验证码发送成功"}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送验证码失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送验证码失败，请稍后重试")


@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    try:
        # 使用优化后的方法，一次性获取用户信息和绑定状态
        user = user_service.get_user_by_token(credentials.credentials, include_binding_status=True, db_session=db)
        if not user:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        return {
            "success": True,
            "data": user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取用户信息失败")

@router.put("/update-profile")
async def update_profile(
    update_data: UpdateProfileRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    try:
        user = user_service.get_user_by_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        return user_service.update_profile(user.id, update_data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="更新失败，请稍后重试")

@router.post("/verify-phone")
async def verify_phone(verify_data: VerifyPhoneRequest, db: Session = Depends(get_db)):
    """验证手机号是否存在"""
    try:
        return user_service.verify_phone(verify_data.phone, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="验证失败，请稍后重试") 

@router.post("/wechat-bind-start")
async def wechat_bind_start(request: Request):
    """开始微信绑定：返回 wxLogin.js 所需参数（appid、redirect_uri、scope、state）
    state 使用前端当前登录 token，用于回调时识别用户。
    """
    try:
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        if not token:
            token = request.query_params.get("token")
        if not token:
            raise HTTPException(status_code=401, detail="未提供认证信息")

        # 参数返回
        appid = os.getenv("WECHAT_OPEN_APP_ID")
        if not appid:
            raise HTTPException(status_code=500, detail="微信开放平台未配置")
        api_base = os.getenv("API_BASE_URL", os.getenv("BASE_URL", "https://api.zdaoyou.chat"))
        redirect_uri = f"{api_base}/api/auth/wechat-bind-callback"
        return {
            "success": True,
            "data": {
                "appid": appid,
                "redirect_uri": redirect_uri,
                "scope": "snsapi_login",
                "state": token,
                "method": "wx_js"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"wechat_bind_start 失败: {str(e)}")
        raise HTTPException(status_code=500, detail="无法发起微信绑定")


@router.get("/wechat-bind-callback")
async def wechat_bind_callback(code: str, state: str, db: Session = Depends(get_db)):
    """微信绑定回调：state 为前端 token。将 openid/unionid 绑定到该用户，完成后跳转 /profile?bind=success"""
    try:
        # 用 state(token) 找到用户
        user_info = user_service.get_user_by_token(state)
        if not user_info:
            raise HTTPException(status_code=401, detail="无效的用户身份")

        from ..services.wechat_service import wechat_service
        wechat_data = wechat_service.get_open_access_token(code)
        openid = wechat_data.get("openid")
        unionid = wechat_data.get("unionid")
        if not openid and not unionid:
            raise HTTPException(status_code=400, detail="微信授权失败")

        # 处理唯一性：如其他账号已占用该 openid/unionid，则将其迁移为当前用户（以当前用户为主）
        from ..models.user import User

        other_user = None
        if unionid:
            other_user = db.query(User).filter(User.unionid == unionid, User.id != str(user_info.id)).first()
        if not other_user and openid:
            other_user = db.query(User).filter(User.openid == openid, User.id != str(user_info.id)).first()

        current = db.query(User).filter(User.id == str(user_info.id)).first()
        if not current:
            raise HTTPException(status_code=404, detail="用户不存在")

        if other_user:
            # 将 other 的聊天等数据迁移给 current，然后清理 other
            from ..models.chat_session import ChatSession
            db.query(ChatSession).filter(ChatSession.user_id == other_user.id).update({ChatSession.user_id: current.id})
            # 释放其微信标识以避免唯一冲突
            other_user.openid = None
            other_user.unionid = None
            db.flush()
            db.delete(other_user)

        # 绑定到当前用户（覆盖）
        current.openid = openid or current.openid
        current.unionid = unionid or current.unionid
        # 尝试写入昵称头像
        try:
            user_info_json = wechat_service.get_user_info(wechat_data.get("access_token", ""), openid) if openid else {}
            if user_info_json.get("nickname"):
                current.wechat_nickname = user_info_json["nickname"]
            if user_info_json.get("headimgurl"):
                current.wechat_avatar = user_info_json["headimgurl"]
        except Exception:
            pass
        current.updated_at = datetime.utcnow()
        db.commit()

        front_base = os.getenv("FRONTBASE_URL", "https://www.zdaoyou.chat")
        return RedirectResponse(url=f"{front_base}/profile?bind=success", status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"wechat_bind_callback 失败: {str(e)}")
        raise HTTPException(status_code=500, detail="微信绑定失败")



 