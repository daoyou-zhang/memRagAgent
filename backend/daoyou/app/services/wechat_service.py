import os
import requests
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
import dotenv
import time
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

class WechatService:
    def __init__(self):
        # 小程序配置
        self.app_id = os.getenv("WECHAT_APP_ID")
        self.app_secret = os.getenv("WECHAT_APP_SECRET")
        # 公众号配置（用于Web端扫码登录）
        self.mp_app_id = os.getenv("WECHAT_MP_APP_ID")
        self.mp_app_secret = os.getenv("WECHAT_MP_APP_SECRET")
        # 开放平台网站应用配置（网站扫码登录）
        self.open_app_id = os.getenv("WECHAT_OPEN_APP_ID")
        self.open_app_secret = os.getenv("WECHAT_OPEN_APP_SECRET")
        # 支付配置（可选）
        self.mch_id = os.getenv("WECHAT_MCH_ID")
        self.mch_key = os.getenv("WECHAT_API_KEY")  # 使用API_KEY作为商户密钥
        self.notify_url = os.getenv("WECHAT_NOTIFY_URL")
        self.cert_path = os.getenv("WECHAT_CERT_PATH")
        self.key_path = os.getenv("WECHAT_KEY_PATH")
        
        # 开发模式配置
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # 强制开发模式（临时修复）
        #self.dev_mode = True
        #logger.warning("强制设置开发模式为True，忽略环境变量设置")
        
        # 支付方式配置
        self.payment_methods = {
            "mock": "模拟支付",
            "alipay": "支付宝",
            "wechat_qr": "微信收款码",
            "paypal": "PayPal"
        }
        
        if not all([self.app_id, self.app_secret]):
            logger.warning("微信小程序配置不完整，小程序登录功能可能无法正常工作")
        
        if not all([self.mp_app_id, self.mp_app_secret]):
            logger.warning("微信公众号配置不完整，Web端扫码登录(公众号授权)可能无法正常工作")
        
        if not all([self.open_app_id, self.open_app_secret]):
            logger.warning("微信开放平台网站应用配置不完整，网站扫码登录(开放平台)可能无法正常工作")
        
        if not all([self.mch_id, self.mch_key]):
            logger.warning("微信支付配置不完整，将使用模拟支付模式")
            self.dev_mode = True
    
    def get_available_payment_methods(self) -> Dict[str, str]:
        """获取可用的支付方式"""
        available_methods = {}
        
        # 仅保留微信支付
        if self.mch_id and self.mch_key:
            available_methods["wechat"] = "微信支付"
        
        # 如果没有任何支付方式，提供模拟支付作为兜底
        if not available_methods:
            logger.error("未配置任何支付方式：缺少商户参数。")
        
        return available_methods

    def get_session_info(self, code: str) -> Dict[str, Any]:
        """通过小程序code获取session_key和openid"""
        try:
            # 开发模式：支持模拟授权码
            if self.dev_mode and code.startswith('mock_'):
                return {
                    "openid": f"mock_openid_{code}",
                    "unionid": f"mock_unionid_{code}",
                    "session_key": f"mock_session_key_{code}"
                }
            
            url = "https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": self.app_id,
                "secret": self.app_secret,
                "js_code": code,
                "grant_type": "authorization_code"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "errcode" in data:
                logger.error(f"微信小程序授权失败: {data}")
                raise HTTPException(status_code=400, detail=f"微信授权失败: {data.get('errmsg', '未知错误')}")
            
            # 检查是否有unionid
            if not data.get("unionid"):
                logger.warning("小程序登录未获取到unionid，建议配置微信开放平台")
            
            return data
        except requests.RequestException as e:
            logger.error(f"微信API请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信服务暂时不可用")
    
    def get_access_token(self, code: str) -> Dict[str, Any]:
        """通过公众号code获取access_token和openid（Web端扫码登录-公众号授权）"""
        try:
            # 开发模式：支持模拟授权码
            if self.dev_mode and code.startswith('mock_'):
                return {
                    "openid": f"mock_openid_{code}",
                    "unionid": f"mock_unionid_{code}",
                    "access_token": f"mock_access_token_{code}"
                }
            
            url = "https://api.weixin.qq.com/sns/oauth2/access_token"
            params = {
                "appid": self.mp_app_id,
                "secret": self.mp_app_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "errcode" in data:
                logger.error(f"微信公众号授权失败: {data}")
                raise HTTPException(status_code=400, detail=f"微信授权失败: {data.get('errmsg', '未知错误')}")
            
            # 检查是否有unionid
            if not data.get("unionid"):
                logger.warning("公众号登录未获取到unionid，建议配置微信开放平台")
            
            return data
        except requests.RequestException as e:
            logger.error(f"微信API请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信服务暂时不可用")

    def get_open_access_token(self, code: str) -> Dict[str, Any]:
        """通过开放平台网站应用code获取access_token和openid（网站扫码登录-开放平台）"""
        try:
           
            url = "https://api.weixin.qq.com/sns/oauth2/access_token"
            params = {
                "appid": self.open_app_id,
                "secret": self.open_app_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if "errcode" in data:
                logger.error(f"微信开放平台授权失败: {data}")
                raise HTTPException(status_code=400, detail=f"微信授权失败: {data.get('errmsg', '未知错误')}")
            return data
        except requests.RequestException as e:
            logger.error(f"微信API请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信服务暂时不可用")
    
    def get_user_info(self, access_token: str, openid: str) -> Dict[str, Any]:
        """获取微信公众号/开放平台用户信息（昵称头像）"""
        try:
            # 开发模式：支持模拟用户信息
            if self.dev_mode and access_token.startswith('mock_'):
                return {
                    "nickname": "测试用户",
                    "headimgurl": "https://img2.imgtp.com/2024/06/28/0Qv8Qw7A.png",
                    "sex": 1,
                    "country": "中国",
                    "province": "北京",
                    "city": "北京",
                    "language": "zh_CN"
                }
            
            url = "https://api.weixin.qq.com/sns/userinfo"
            params = {
                "access_token": access_token,
                "openid": openid,
                "lang": "zh_CN"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "errcode" in data:
                logger.error(f"获取微信用户信息失败: {data}")
                raise HTTPException(status_code=400, detail="获取微信用户信息失败")
            
            return data
        except requests.RequestException as e:
            logger.error(f"微信API请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail="微信服务暂时不可用")
    
    def decrypt_user_info(self, session_key: str, encrypted_data: str, iv: str) -> Dict[str, Any]:
        """解密小程序用户信息"""
        try:
            # 这里需要实现小程序用户信息解密
            # 由于需要cryptography库，这里先返回模拟数据
            # 实际项目中需要安装: pip install cryptography

            # 模拟解密后的用户信息
            return {
                "nickName": "微信用户",
                "avatarUrl": "",
                "gender": 0,
                "country": "",
                "province": "",
                "city": "",
                "language": "zh_CN"
            }
        except Exception as e:
            logger.error(f"解密用户信息失败: {str(e)}")
            raise HTTPException(status_code=400, detail="获取用户信息失败")
    
    def create_payment_order(self, user_id: str, amount: float, description: str, payment_method: str = "mock") -> Dict[str, Any]:
        """创建支付订单"""
        try:
            if payment_method == "mock" or self.dev_mode:
                # 开发模式：返回模拟支付数据
                return self._create_mock_payment(user_id, amount, description)
            elif payment_method == "wechat":
                # 微信支付
                return self._create_wechat_payment(user_id, amount, description)
            elif payment_method == "alipay":
                # 支付宝支付
                return self._create_alipay_payment(user_id, amount, description)
            elif payment_method == "paypal":
                # PayPal支付
                return self._create_paypal_payment(user_id, amount, description)
            else:
                raise HTTPException(status_code=400, detail=f"不支持的支付方式: {payment_method}")
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}")
            raise HTTPException(status_code=500, detail="创建支付订单失败")
    
    def _create_wechat_payment(self, user_id: str, amount: float, description: str, trade_type: str = "NATIVE", openid: str = None, time_expire: Optional[str] = None) -> Dict[str, Any]:
        """创建微信支付订单"""
        try:
            # 检查支付配置
            if not all([self.app_id, self.mch_id, self.mch_key]):
                logger.error("微信支付配置不完整，缺少 app_id/mch_id/API_KEY")
                raise HTTPException(status_code=500, detail="微信支付配置不完整")
            
            # 生成符合微信支付规范的订单号（最大32字符）
            # 格式：RW + 用户ID后8位 + 时间戳后10位
            user_id_str = str(user_id)  # 将UUID转换为字符串
            user_id_suffix = user_id_str[-8:] if len(user_id_str) > 8 else user_id_str.zfill(8)
            timestamp_suffix = str(int(time.time()))[-10:]
            out_trade_no = f"RW{user_id_suffix}{timestamp_suffix}"
            
            # 确保订单号不超过32字符
            if len(out_trade_no) > 32:
                out_trade_no = out_trade_no[:32]

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "nonce_str": self._generate_nonce_str(),
                "body": description,
                "out_trade_no": out_trade_no,
                "total_fee": int(amount * 100),  # 转换为分
                "spbill_create_ip": os.getenv('SERVER_IP', '127.0.0.1'),
                "notify_url": self.notify_url or f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/reward/payment-callback",
                "trade_type": trade_type  # 支付类型：NATIVE(扫码)、JSAPI(公众号)
            }

            # 透传支付结束时间（格式：yyyyMMddHHmmss）
            if time_expire:
                params["time_expire"] = time_expire
          
            # 仅允许 NATIVE（扫码）与 JSAPI（用于小程序/公众号）。不支持 H5(MWEB) 支付。
            if trade_type == "MWEB":
                logger.error("已禁用H5(MWEB)支付")
                raise HTTPException(status_code=400, detail="支付方式已禁用")
            if trade_type == "JSAPI" and openid:
                params["openid"] = openid
            if trade_type == "NATIVE":
                # Native 扫码必传 product_id（用于识别商品/订单）
                params["product_id"] = out_trade_no
        
            # 添加签名
            params["sign"] = self._generate_sign(params)
            
            # 调用微信统一下单接口
            xml_data = self._dict_to_xml(params)
            response = requests.post(
                "https://api.mch.weixin.qq.com/pay/unifiedorder",
                data=xml_data,
                headers={"Content-Type": "application/xml"},
                timeout=10
            )
            
            # 解析响应
            result = self._xml_to_dict(response.text)
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                # 根据支付类型返回不同数据
                payment_data = {
                    "order_id": out_trade_no,
                    "amount": amount,
                    "description": description,
                    "status": "pending",
                    "dev_mode": False,
                    "message": "微信支付订单创建成功",
                    "payment_method": "wechat",
                    "trade_type": trade_type
                }
                
                if trade_type == "NATIVE":
                    # 扫码支付：返回二维码
                    payment_data["qr_code"] = result.get("code_url")
                    payment_data["payment_url"] = result.get("code_url")
                elif trade_type == "JSAPI":
                    # 公众号支付：返回支付参数
                    payment_data["jsapi_params"] = self._generate_jsapi_params(result.get("prepay_id"))
                elif trade_type == "MWEB":
                    # H5支付：返回支付链接
                    payment_data["mweb_url"] = result.get("mweb_url")
                
                return payment_data
            else:
                logger.error(f"微信支付下单失败: {result}")
                raise HTTPException(status_code=400, detail="微信支付下单失败")
                
        except Exception as e:
            logger.error(f"微信支付创建失败: {str(e)}")
            raise
    
    def _create_alipay_payment(self, user_id: str, amount: float, description: str) -> Dict[str, Any]:
        """创建支付宝支付订单"""
        # 这里需要集成支付宝SDK
        # 实际项目中需要安装: pip install alipay-sdk-python
        
        # 生成符合规范的订单号
        user_id_str = str(user_id)  # 将UUID转换为字符串
        user_id_suffix = user_id_str[-8:] if len(user_id_str) > 8 else user_id_str.zfill(8)
        timestamp_suffix = str(int(time.time()))[-10:]
        out_trade_no = f"AL{user_id_suffix}{timestamp_suffix}"
        
        order_data = {
            "out_trade_no": out_trade_no,
            "total_amount": str(amount),
            "subject": description,
            "payment_method": "alipay"
        }

        return order_data
    
    def _create_mock_payment(self, user_id: str, amount: float, description: str) -> Dict[str, Any]:
        """创建模拟支付订单"""
        # 生成符合规范的订单号
        user_id_str = str(user_id)  # 将UUID转换为字符串
        user_id_suffix = user_id_str[-8:] if len(user_id_str) > 8 else user_id_str.zfill(8)
        timestamp_suffix = str(int(time.time()))[-10:]
        order_id = f"MK{user_id_suffix}{timestamp_suffix}"
        
        mock_payment = {
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "status": "pending",
            "payment_url": f"mock://payment/{order_id}",
            "qr_code": f"mock://qr/{order_id}",
            "dev_mode": True,
            "message": "开发模式：模拟支付订单",
            "payment_method": "mock"
        }
        
        return mock_payment

    def _create_paypal_payment(self, user_id: str, amount: float, description: str) -> Dict[str, Any]:
        """创建PayPal支付订单"""
        # 这里需要集成PayPal SDK
        # 实际项目中需要安装: pip install paypalrestsdk
        order_data = {
            "out_trade_no": f"reward_{user_id}_{int(time.time())}",
            "total_amount": str(amount),
            "currency": "USD",  # PayPal支持多种货币
            "description": description,
            "payment_method": "paypal",
            "return_url": f"{os.getenv('BASE_URL', 'http://localhost:3000')}/payment/success",
            "cancel_url": f"{os.getenv('BASE_URL', 'http://localhost:3000')}/payment/cancel"
        }
        
        logger.info(f"创建PayPal支付订单: {order_data}")
        return order_data

    def process_mock_payment(self, order_id: str) -> Dict[str, Any]:
        """处理模拟支付"""
        try:
            # 模拟支付成功
            result = {
                "success": True,
                "order_id": order_id,
                "status": "paid",
                "paid_amount": 0.01,  # 模拟金额
                "paid_time": time.time(),
                "dev_mode": True,
                "message": "开发模式：支付成功",
                "payment_method": "mock"
            }
            
            logger.info(f"模拟支付成功: {result}")
            return result
        except Exception as e:
            logger.error(f"模拟支付处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail="支付处理失败")

    def transfer_to_user(self, openid: str, amount: float, description: str) -> bool:
        """企业付款到零钱"""
        try:
            if self.dev_mode:
                # 开发模式：模拟转账
                return True
            
            # 检查支付配置
            if not all([self.app_id, self.mch_id, self.mch_key]):
                logger.error("微信支付配置不完整，无法进行企业付款")
                return False
            
            # 生产模式：调用微信企业付款API
            transfer_data = {
                "mch_appid": self.app_id,
                "mchid": self.mch_id,
                "nonce_str": self._generate_nonce_str(),
                "partner_trade_no": f"transfer_{int(time.time())}",
                "openid": openid,
                "check_name": "NO_CHECK",
                "amount": int(amount * 100),  # 转换为分
                "desc": description,
                "spbill_create_ip": os.getenv('SERVER_IP', '127.0.0.1')
            }
            
            # 添加签名
            transfer_data["sign"] = self._generate_sign(transfer_data)
            
            # 调用微信企业付款接口
            xml_data = self._dict_to_xml(transfer_data)
            response = requests.post(
                "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers",
                data=xml_data,
                headers={"Content-Type": "application/xml"},
                timeout=10,
                cert=(self.cert_path, self.key_path) if self.cert_path and self.key_path else None
            )
            
            # 解析响应
            result = self._xml_to_dict(response.text)
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return True
            else:
                logger.error(f"企业付款失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"企业付款失败: {str(e)}")
            return False
    
    def _generate_nonce_str(self) -> str:
        """生成随机字符串"""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成微信支付签名"""
        # 过滤空值和sign参数
        filtered_params = {k: v for k, v in params.items() if v and k != 'sign'}
        
        # 按参数名ASCII码从小到大排序
        sorted_params = sorted(filtered_params.items())
        
        # 拼接字符串
        sign_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        sign_string += f"&key={self.mch_key}"
        
        # MD5加密并转大写
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    
    def _dict_to_xml(self, data: Dict[str, Any]) -> str:
        """字典转XML"""
        xml_elements = ['<xml>']
        for key, value in data.items():
            xml_elements.append(f'<{key}>{value}</{key}>')
        xml_elements.append('</xml>')
        return ''.join(xml_elements)
    
    def _xml_to_dict(self, xml_string: str) -> Dict[str, Any]:
        """XML转字典"""
        try:
            root = ET.fromstring(xml_string)
            return {child.tag: child.text for child in root}
        except Exception as e:
            logger.error(f"XML解析失败: {str(e)}")
            return {}
    
    def verify_payment_signature(self, params: Dict[str, Any], sign: str) -> bool:
        """验证微信支付回调签名"""
        try:
            calculated_sign = self._generate_sign(params)
            return calculated_sign == sign
        except Exception as e:
            logger.error(f"签名验证失败: {str(e)}")
            return False
    
    def _generate_jsapi_params(self, prepay_id: str) -> Dict[str, Any]:
        """生成JSAPI支付参数"""
        import time
        import random
        import string
        
        # 生成随机字符串
        nonce_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        timestamp = str(int(time.time()))
        
        # 构建支付参数
        params = {
            "appId": self.app_id,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": f"prepay_id={prepay_id}",
            "signType": "MD5"
        }
        
        # 生成签名
        sign_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        sign_string += f"&key={self.mch_key}"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
        
        params["paySign"] = sign
        return params

# 创建微信服务实例
wechat_service = WechatService() 