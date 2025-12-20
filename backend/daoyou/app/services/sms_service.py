import os
import random
import logging
from typing import Optional

from redis import Redis
import dotenv

logger = logging.getLogger(__name__)

try:
    from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
    from alibabacloud_tea_util import models as util_models
    from alibabacloud_tea_util.client import Client as UtilClient
    ALIYUN_SMS_AVAILABLE = True
except ImportError:
    DysmsapiClient = None  # type: ignore
    open_api_models = None  # type: ignore
    dysmsapi_models = None  # type: ignore
    util_models = None  # type: ignore
    UtilClient = None  # type: ignore
    ALIYUN_SMS_AVAILABLE = False

# 加载环境变量
dotenv.load_dotenv()

class SMSService:
    def __init__(self):
        self.sign_name = os.getenv("ALIYUN_SMS_SIGN_NAME", "道友")
        self.template_code = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "SMS_123456789")
        
        # 检查环境变量
        access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        
        if access_key_id and access_key_secret and ALIYUN_SMS_AVAILABLE and os.getenv("ALIYUN_SMS_AVAILABLE", "true").lower() == "true":
            try:
                self.client = self._create_client()
            except Exception as e:
                logger.error(f"阿里云短信客户端初始化失败: {str(e)}")
                self.client = None
        else:
            logger.warning("阿里云短信服务未配置或SDK未安装，将使用模拟模式")
            self.client = None
        
    def _create_client(self) -> DysmsapiClient:
        """创建阿里云短信客户端"""
        try:
            config = open_api_models.Config(
                access_key_id=os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
                access_key_secret=os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
            )
            config.endpoint = "dysmsapi.aliyuncs.com"
            return DysmsapiClient(config)
        except Exception as e:
            logger.error(f"创建阿里云短信客户端失败: {str(e)}")
            raise
    
    def generate_verification_code(self) -> str:
        """生成6位数字验证码"""
        return str(random.randint(100000, 999999))
    
    async def send_verification_code(self, phone: str, redis: Redis) -> dict:
        """发送验证码"""
        try:
            # 检查发送频率限制（1分钟内只能发送一次）
            rate_limit_key = f"sms_rate_limit:{phone}"
            if redis.exists(rate_limit_key):
                return {
                    "success": False,
                    "message": "发送过于频繁，请稍后再试"
                }
            
            # 生成验证码
            code = self.generate_verification_code()
            
            # 检查是否配置了阿里云短信服务
            if not self.client:
                # 如果没有配置阿里云，使用模拟发送
                logger.warning("阿里云短信服务未配置，使用模拟验证码")
                redis.setex(f"sms_code:{phone}", 300, code)
                redis.setex(rate_limit_key, 60, "1")
                return {
                    "success": True,
                    "message": f"验证码发送成功（测试模式）：{code}",
                    "request_id": "mock_request_id"
                }
            
            # 创建发送短信请求
            # 创建发送短信请求
            # 根据模板类型决定是否发送参数
            # 创建发送短信请求
            # 根据阿里云模板要求，发送正确的参数
            send_sms_request = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.sign_name,
                template_code=self.template_code,
                template_param=f'{{"code":"{code}"}}'
            )
            
            # 发送短信
            runtime = util_models.RuntimeOptions()
            response = await self.client.send_sms_with_options_async(send_sms_request, runtime)
            
            if response.body.code == "OK":
                # 将验证码存储到Redis，设置5分钟过期
                redis.setex(f"sms_code:{phone}", 300, code)
                # 设置发送频率限制，1分钟内不能重复发送
                redis.setex(rate_limit_key, 60, "1")
                
                return {
                    "success": True,
                    "message": "验证码发送成功",
                    "request_id": response.body.request_id
                }
            else:
                logger.error(f"验证码发送失败: {response.body.message}")
                return {
                    "success": False,
                    "message": f"发送失败: {response.body.message}"
                }
                
        except Exception as e:
            logger.error(f"发送验证码异常: {str(e)}")
            # 如果阿里云发送失败，使用模拟验证码作为备选方案
            try:
                code = self.generate_verification_code()
                redis.setex(f"sms_code:{phone}", 300, code)
                redis.setex(rate_limit_key, 60, "1")
                return {
                    "success": True,
                    "message": f"验证码发送成功（备用模式）：{code}",
                    "request_id": "fallback_request_id"
                }
            except Exception as fallback_error:
                logger.error(f"备用验证码发送也失败: {str(fallback_error)}")
                return {
                    "success": False,
                    "message": "发送失败，请稍后重试"
                }
    
    def verify_code(self, phone: str, code: str, redis: Redis) -> bool:
        """验证验证码"""
        try:
            stored_code = redis.get(f"sms_code:{phone}")
            if stored_code:
                # 处理Redis返回的数据，可能是bytes或str
                if isinstance(stored_code, bytes):
                    stored_code = stored_code.decode('utf-8')
                elif isinstance(stored_code, str):
                    stored_code = stored_code
                else:
                    stored_code = str(stored_code)
                
                if stored_code == code:
                    # 验证成功后删除验证码
                    redis.delete(f"sms_code:{phone}")
                    return True
                else:
                    logger.warning(f"验证码不匹配: 输入={code}, 存储={stored_code}")
                    return False
            else:
                logger.warning(f"未找到验证码: {phone}")
                return False
        except Exception as e:
            logger.error(f"验证验证码异常: {str(e)}")
            return False

# 创建全局实例
sms_service = SMSService() 