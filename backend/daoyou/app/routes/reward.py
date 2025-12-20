from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from sqlalchemy.orm import Session
from uuid import uuid4
import logging
import os
from ..core.database import get_db
from ..models.reward import Reward, Base
from sqlalchemy import and_, text
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..services.auth_service import user_service
from ..services.wechat_service import wechat_service
import redis

logger = logging.getLogger(__name__)

router = APIRouter()

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    user = user_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    return user.id

def get_current_user_phone(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    user = user_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    return user.phone

@router.post('/addreward')
async def reward(data: dict, db: Session = Depends(get_db)):
    """打赏接口 - 保持向后兼容"""
    user_phone = data.get('userPhone')
    amount = data.get('amount')
    if not user_phone or not amount or float(amount) <= 0:
        raise HTTPException(status_code=400, detail='参数错误')
    # 金额上限校验
    if float(amount) > 100:
        raise HTTPException(status_code=400, detail='单笔打赏金额上限为100元')
    reward = Reward(id=str(uuid4()), user_phone=user_phone, amount=float(amount))
    db.add(reward)
    db.commit()
    return {"success": True, "message": "打赏成功"}

@router.post('/reward')
async def create_reward(
    data: dict, 
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """新的打赏接口 - 基于用户ID，支持推荐者分成"""
    amount = data.get('amount')
    if not amount or float(amount) <= 0:
        raise HTTPException(status_code=400, detail='打赏金额必须大于0')
    # 金额上限校验
    if float(amount) > 100:
        raise HTTPException(status_code=400, detail='单笔打赏金额上限为100元')
    
    # 获取当前用户信息（使用current_user_id而不是token）
    current_user = user_service.get_user_by_id(current_user_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    
    # 创建打赏记录
    reward = Reward(
        id=str(uuid4()), 
        user_phone=current_user.phone or f"wechat_{current_user.openid}",
        amount=float(amount)
    )
    db.add(reward)
    db.commit()
    
    # 处理推荐者分成
    if current_user.referrer_id:
        await process_referrer_commission(current_user.referrer_id, float(amount), db)
    
    return {"success": True, "message": "打赏成功"}

@router.get('/wechat-pay')
async def wechat_pay_health_check():
    """微信支付健康检查端点"""
    return {"status": "ok", "message": "微信支付服务正常"}

@router.post('/wechat-pay')
async def create_wechat_payment(
    data: dict,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """创建微信支付订单"""
    amount = data.get('amount')
    payment_method = data.get('payment_method', 'wechat')  # 默认使用微信支付
    trade_type = data.get('trade_type', 'NATIVE')  # 支付类型：NATIVE(扫码)、JSAPI(小程序/公众号)、MWEB(H5)
    
    if not amount or float(amount) <= 0:
        raise HTTPException(status_code=400, detail='打赏金额必须大于0')
    # 金额上限校验
    if float(amount) > 100:
        raise HTTPException(status_code=400, detail='单笔打赏金额上限为100元')
    
    # 获取当前用户信息（使用current_user_id而不是token）
    current_user = user_service.get_user_by_id(current_user_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    

    # 检查JSAPI支付的必要条件
    if trade_type == "JSAPI":
        # 直接使用主表的openid，这个应该是登录时获取的正确openid
        user_openid = current_user.openid
        
        if not user_openid:
            logger.error(f"用户 {current_user_id} 没有openid，无法使用JSAPI支付")
            raise HTTPException(status_code=400, detail="用户未绑定微信，无法使用小程序支付")

    else:
        user_openid = None
    
    # 创建支付订单
    try:
        if payment_method == "wechat":
            # 微信支付，根据trade_type调用不同的支付方式
            payment_data = wechat_service._create_wechat_payment(
                user_id=current_user_id,
                amount=float(amount),
                description="用户打赏",
                trade_type=trade_type,
                openid=user_openid if trade_type == "JSAPI" else None
            )
            

            # 保存订单号到用户ID的映射（用于回调时查找用户）
            # 这里可以将映射保存到Redis或数据库中
            try:
                from ..services.rate_limit_service import rate_limit_service
                # 映射TTL提高至3小时，覆盖code_url(2h)并留缓冲
                # 将UUID转换为字符串
                user_id_str = str(current_user_id)
                rate_limit_service.redis.setex(f"order_user:{payment_data['order_id']}", 10800, user_id_str)
               
            except Exception as e:
                logger.warning(f"保存订单映射失败: {str(e)}")
                # Redis连接失败不影响支付流程，继续执行

            # 数据库兜底映射（避免Redis失效）
            try:
                db.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS payment_order_map (
                        order_id VARCHAR(64) PRIMARY KEY,
                        user_id UUID NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                    )
                    """
                ))
                db.execute(text(
                    """
                    INSERT INTO payment_order_map(order_id, user_id)
                    VALUES (:order_id, :user_id)
                    ON CONFLICT (order_id) DO NOTHING
                    """
                ), {"order_id": payment_data['order_id'], "user_id": current_user_id})
                db.commit()
            except Exception as e:
                logger.warning(f"订单映射(DB)保存失败: {str(e)}")
                
        else:
            # 其他支付方式
            payment_data = wechat_service.create_payment_order(
                user_id=current_user_id,
                amount=float(amount),
                description="用户打赏",
                payment_method=payment_method
            )
        
        return {
            "success": True,
            "message": "支付订单创建成功",
            "data": payment_data,
            "payment_method": payment_method,
            "trade_type": trade_type
        }
    except Exception as e:
        logger.error(f"创建支付订单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")

@router.get('/payment-methods')
async def get_payment_methods():
    """获取可用的支付方式"""
    try:
        available_methods = wechat_service.get_available_payment_methods()
        return {
            "success": True,
            "data": available_methods
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支付方式失败: {str(e)}")

@router.post('/payment-callback')
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    """微信支付回调处理"""
    try:
        # 兜底：确保映射表存在
        try:
            db.execute(text(
                """
                CREATE TABLE IF NOT EXISTS payment_order_map (
                    order_id VARCHAR(64) PRIMARY KEY,
                    user_id UUID NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                )
                """
            ))
            db.commit()
        except Exception as e:
            logger.warning(f"确保映射表存在失败: {str(e)}")
        # 读取XML数据
        xml_data = await request.body()
        xml_string = xml_data.decode('utf-8')
        
        # 解析XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_string)
        callback_data = {child.tag: child.text for child in root}
        
        # 验证签名
        sign = callback_data.pop('sign', '')
        if not wechat_service.verify_payment_signature(callback_data, sign):
            logger.error("微信支付回调签名验证失败")
            return Response(content="<xml><return_code>FAIL</return_code><return_msg>签名验证失败</return_msg></xml>", media_type="text/xml")
        
        # 验证支付结果
        payment_success = callback_data.get('result_code') == 'SUCCESS'
        out_trade_no = callback_data.get('out_trade_no')
        total_fee = int(callback_data.get('total_fee', 0)) / 100  # 转换为元
        
        if not payment_success:
            logger.warning(f"微信支付失败: {callback_data}")
            return Response(content="<xml><return_code>SUCCESS</return_code><return_msg>OK</return_msg></xml>", media_type="text/xml")
        
        # 解析订单号获取用户ID
        # 新格式: RW{user_id_suffix}{timestamp_suffix} 或 MK{user_id_suffix}{timestamp_suffix}
        try:
            # 首先尝试从Redis获取用户ID映射
            user_id = None
            try:
                from ..services.rate_limit_service import rate_limit_service
                user_id = rate_limit_service.redis.get(f"order_user:{out_trade_no}")
                if user_id:
                    user_id = user_id.decode('utf-8')
                    # 获取成功后删除映射
                    rate_limit_service.redis.delete(f"order_user:{out_trade_no}")
            except Exception as e:
                logger.warning(f"从Redis获取用户ID映射失败: {str(e)}")
                # Redis连接失败不影响支付流程，继续执行
            
            # 如果Redis中没有找到，尝试解析订单号
            if not user_id:
                if out_trade_no.startswith('RW'):
                    # 微信支付订单号格式: RW + 用户ID后8位 + 时间戳后10位
                    # 由于无法从8位后缀反推完整UUID，这里需要其他方案
                    # DB 兜底：查询映射表
                    try:
                        result = db.execute(text("SELECT user_id FROM payment_order_map WHERE order_id = :oid"), {"oid": out_trade_no}).first()
                        if result and result[0]:
                            user_id = str(result[0])
                        else:
                            logger.error(f"无法从订单号解析用户ID: {out_trade_no}，Redis与DB映射均缺失")
                            return Response(content="<xml><return_code>FAIL</return_code><return_msg>无法识别用户</return_msg></xml>", media_type="text/xml")
                    except Exception as e:
                        logger.error(f"查询DB映射失败: {str(e)}")
                        return Response(content="<xml><return_code>FAIL</return_code><return_msg>无法识别用户</return_msg></xml>", media_type="text/xml")
                elif out_trade_no.startswith('MK'):
                    # 模拟支付订单号格式: MK + 用户ID后8位 + 时间戳后10位
                    try:
                        result = db.execute(text("SELECT user_id FROM payment_order_map WHERE order_id = :oid"), {"oid": out_trade_no}).first()
                        if result and result[0]:
                            user_id = str(result[0])
                        else:
                            logger.error(f"无法从订单号解析用户ID: {out_trade_no}，Redis与DB映射均缺失")
                            return Response(content="<xml><return_code>FAIL</return_code><return_msg>无法识别用户</return_msg></xml>", media_type="text/xml")
                    except Exception as e:
                        logger.error(f"查询DB映射失败: {str(e)}")
                        return Response(content="<xml><return_code>FAIL</return_code><return_msg>无法识别用户</return_msg></xml>", media_type="text/xml")
                else:
                    # 兼容旧格式: reward_{user_id}_{timestamp}
                    try:
                        user_id = out_trade_no.split('_')[1]
                    except:
                        logger.error(f"无效的订单号格式: {out_trade_no}")
                        return Response(content="<xml><return_code>FAIL</return_code><return_msg>无效的订单号</return_msg></xml>", media_type="text/xml")
        except:
            logger.error(f"无效的订单号: {out_trade_no}")
            return Response(content="<xml><return_code>FAIL</return_code><return_msg>无效的订单号</return_msg></xml>", media_type="text/xml")
        
        # 确保获取到有效的用户ID
        if not user_id:
            logger.error(f"无法获取用户ID，订单号: {out_trade_no}")
            return {"return_code": "FAIL", "return_msg": "无法识别用户"}

        # 检查是否已经处理过
        existing_reward = db.query(Reward).filter(Reward.id == out_trade_no).first()
        if existing_reward:
            return {"return_code": "SUCCESS", "return_msg": "OK"}
        
        # 创建打赏记录
        current_user = user_service.get_user_by_id(user_id)
        if not current_user:
            logger.error(f"用户不存在: {user_id}")
            return Response(content="<xml><return_code>FAIL</return_code><return_msg>用户不存在</return_msg></xml>", media_type="text/xml")
        
        reward = Reward(
            id=out_trade_no,  # 使用微信订单号作为ID
            user_phone=current_user.phone or f"wechat_{current_user.openid}",
            amount=total_fee
        )
        db.add(reward)
        db.commit()

        # 清理DB映射（已消费）
        try:
            db.execute(text("DELETE FROM payment_order_map WHERE order_id = :oid"), {"oid": out_trade_no})
            db.commit()
        except Exception:
            pass
        
        # 处理推荐者分成
        if current_user.referrer_id:
            await process_referrer_commission(current_user.referrer_id, total_fee, db)
        
        return Response(content="<xml><return_code>SUCCESS</return_code><return_msg>OK</return_msg></xml>", media_type="text/xml")
        
    except Exception as e:
        logger.error(f"微信支付回调处理失败: {str(e)}")
        return Response(content="<xml><return_code>FAIL</return_code><return_msg>处理失败</return_msg></xml>", media_type="text/xml")

@router.get('/payment-status/{order_id}')
async def check_payment_status(order_id: str, db: Session = Depends(get_db)):
    """查询支付状态"""
    try:
        # 检查数据库中是否有对应的打赏记录
        reward = db.query(Reward).filter(Reward.id == order_id).first()
        
        if reward:
            return {
                "success": True,
                "data": {
                    "status": "paid",
                    "amount": reward.amount,
                    "paid_time": reward.created_at.isoformat() if reward.created_at else None
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "status": "pending",
                    "message": "订单待支付"
                }
            }
    except Exception as e:
        logger.error(f"查询支付状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询支付状态失败")

async def process_referrer_commission(referrer_id: str, amount: float, db: Session):
    """处理推荐者分成"""
    try:
        # 检查是否启用推荐者分成功能
        enable_commission = os.getenv("ENABLE_REFERRER_COMMISSION", "true").lower() == "true"
        if not enable_commission:
            return
        
        # 获取推荐者信息
        referrer = user_service.get_user_by_id(referrer_id)
        if not referrer or not referrer.openid:
            return
        
        # 获取分成比例，默认30%
        commission_rate = float(os.getenv("REFERRER_COMMISSION_RATE", "0.3"))
        commission_amount = amount * commission_rate
        
        # 通过微信企业付款给推荐者
        success = wechat_service.transfer_to_user(
            openid=referrer.openid,
            amount=commission_amount,
            description="推荐分成"
        )
        
        if success:
            # 记录分成记录（可以创建新的表）
            logger.info(f"推荐者分成成功: {referrer_id} -> {commission_amount}元 (比例: {commission_rate*100}%)")
        else:
            logger.error(f"推荐者分成失败: {referrer_id} -> {commission_amount}元")
            
    except Exception as e:
        logger.error(f"处理推荐者分成失败: {str(e)}")

@router.get('/list')
async def reward_list(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=20),
    userPhone: str = '',
    min: Optional[str] = '',
    max: Optional[str] = '',
    current_phone: str = Depends(get_current_user_phone)
):
    # 只允许手机号为 15948640987 的用户访问
    if current_phone != '15948640987':
        raise HTTPException(status_code=403, detail="无权访问")
    query = db.query(Reward)
    if userPhone:
        query = query.filter(Reward.user_phone == userPhone)
    try:
        min_value = float(min) if min else 0
    except Exception:
        min_value = 0
    try:
        max_value = float(max) if max else 0
    except Exception:
        max_value = 0
    if min_value > 0:
        query = query.filter(Reward.amount >= min_value)
    if max_value > 0:
        query = query.filter(Reward.amount <= max_value)
    total = query.count()
    records = query.order_by(Reward.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {"success": True, "data": {"records": [
        {"id": r.id, "user_phone": r.user_phone, "amount": r.amount, "created_at": r.created_at.strftime('%Y-%m-%d %H:%M:%S')} for r in records
    ], "total": total}} 