"""
Rate Limit Service

这个模块提供了请求频率限制和用户配额控制功能。
主要功能包括：
- 基于手机号的请求频率限制
- 基于时间窗口的配额控制
- 异常请求检测和告警
"""

import time
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import redis
from redis.connection import ConnectionPool
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class RateLimitService:
    def __init__(
        self,
        redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379"),
        redis_password: str = os.getenv("REDIS_PASSWORD", ""),
        redis_db: int = int(os.getenv("REDIS_DB", "0")),
        max_requests_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
        max_requests_per_hour: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "100")),
        max_requests_per_day: int = int(os.getenv("RATE_LIMIT_PER_DAY", "500")),
        global_max_requests_per_minute: int = int(os.getenv("GLOBAL_RATE_LIMIT_PER_MINUTE", "300")),
        global_max_requests_per_hour: int = int(os.getenv("GLOBAL_RATE_LIMIT_PER_HOUR", "3000")),
        global_max_requests_per_day: int = int(os.getenv("GLOBAL_RATE_LIMIT_PER_DAY", "15000")),
        block_duration: int = int(os.getenv("BLOCK_DURATION", "3600")),
        max_retries: int = 3,
        retry_delay: int = 1,
    ):
        """初始化限流服务
        
        Args:
            redis_url: Redis连接URL
            redis_password: Redis密码
            redis_db: Redis数据库编号
            max_requests_per_minute: 单个用户每分钟最大请求数
            max_requests_per_hour: 单个用户每小时最大请求数
            max_requests_per_day: 单个用户每天最大请求数
            global_max_requests_per_minute: 全局每分钟最大请求数
            global_max_requests_per_hour: 全局每小时最大请求数
            global_max_requests_per_day: 全局每天最大请求数
            block_duration: 违规后封禁时长（秒）
            max_retries: Redis连接最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 创建连接池
        self.pool = ConnectionPool.from_url(
            redis_url,
            password=redis_password,
            db=redis_db,
            decode_responses=True,
            max_connections=10,
            socket_timeout=10,  # 增加超时时间以支持SSH隧道
            socket_connect_timeout=10,  # 增加连接超时时间
        )
        
        # 尝试连接Redis
        self._connect_redis()
        
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour
        self.max_requests_per_day = max_requests_per_day
        self.global_max_requests_per_minute = global_max_requests_per_minute
        self.global_max_requests_per_hour = global_max_requests_per_hour
        self.global_max_requests_per_day = global_max_requests_per_day
        self.block_duration = block_duration
        
    def _connect_redis(self) -> None:
        """连接Redis服务器，支持重试"""
        for attempt in range(self.max_retries):
            try:
                self.redis = redis.Redis(connection_pool=self.pool)
                self.redis.ping()  # 测试连接
                return
            except redis.ConnectionError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Redis连接失败，第{attempt + 1}次重试: {str(e)}")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Redis连接失败，已达到最大重试次数: {str(e)}")
                    raise RuntimeError("无法连接到Redis服务器，请检查Redis配置")
            except Exception as e:
                logger.error(f"Redis连接发生未知错误: {str(e)}")
                raise RuntimeError(f"Redis连接错误: {str(e)}")
                
    def _execute_with_retry(self, func, *args, **kwargs):
        """执行Redis操作，支持重试"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except redis.ConnectionError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Redis操作失败，第{attempt + 1}次重试: {str(e)}")
                    self._connect_redis()  # 重新连接
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Redis操作失败，已达到最大重试次数: {str(e)}")
                    raise RuntimeError("Redis操作失败，请检查Redis服务状态")
            except Exception as e:
                logger.error(f"Redis操作发生未知错误: {str(e)}")
                raise RuntimeError(f"Redis操作错误: {str(e)}")

    def _get_key(self, phone: str, time_window: str) -> str:
        """生成Redis键
        
        Args:
            phone: 用户手机号
            time_window: 时间窗口（minute/hour/day）
            
        Returns:
            Redis键
        """
        return f"rate_limit:{phone}:{time_window}"
        
    def _get_global_key(self, time_window: str) -> str:
        """生成全局Redis键
        
        Args:
            time_window: 时间窗口（minute/hour/day）
            
        Returns:
            Redis键
        """
        return f"global_rate_limit:{time_window}"
        
    def _is_blocked(self, phone: str) -> bool:
        """检查用户是否被封禁"""
        return bool(self._execute_with_retry(self.redis.get, f"blocked:{phone}"))
        
    def _block_user(self, phone: str) -> None:
        """封禁用户"""
        self._execute_with_retry(
            self.redis.setex,
            f"blocked:{phone}",
            self.block_duration,
            "1"
        )
        logger.warning(f"用户 {phone} 因请求频率过高被封禁 {self.block_duration} 秒")
        
    def _check_rate_limit(self, phone: str, time_window: str, max_requests: int) -> bool:
        """检查请求频率限制"""
        key = self._get_key(phone, time_window)
        current = self._execute_with_retry(self.redis.incr, key)
        
        if current == 1:
            # 设置过期时间
            expire_time = {
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(time_window, 60)
            self._execute_with_retry(self.redis.expire, key, expire_time)
                
        return current > max_requests
        
    def _check_global_rate_limit(self, time_window: str, max_requests: int) -> bool:
        """检查全局请求频率限制"""
        key = self._get_global_key(time_window)
        current = self._execute_with_retry(self.redis.incr, key)
        
        if current == 1:
            # 设置过期时间
            expire_time = {
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(time_window, 60)
            self._execute_with_retry(self.redis.expire, key, expire_time)
                
        return current > max_requests
        
    def check_request(self, phone: str) -> None:
        """检查用户请求是否合法
        
        Args:
            phone: 用户手机号
            
        Raises:
            HTTPException: 如果请求不合法
        """
        # 检查是否被封禁
        if self._is_blocked(phone):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试"
            )
            
        # 检查全局请求频率
        if self._check_global_rate_limit("minute", self.global_max_requests_per_minute):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="系统当前请求量过大，请稍后再试"
            )
            
        if self._check_global_rate_limit("hour", self.global_max_requests_per_hour):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="系统当前请求量过大，请稍后再试"
            )
            
        if self._check_global_rate_limit("day", self.global_max_requests_per_day):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="系统今日请求量已达上限，请明天再试"
            )
            
        # 检查用户请求频率
        if self._check_rate_limit(phone, "minute", self.max_requests_per_minute):
            self._block_user(phone)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试"
            )
            
        if self._check_rate_limit(phone, "hour", self.max_requests_per_hour):
            self._block_user(phone)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试"
            )
            
        if self._check_rate_limit(phone, "day", self.max_requests_per_day):
            self._block_user(phone)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="今日请求次数已达上限，请明天再试"
            )
            
    def get_user_stats(self, phone: str) -> Dict[str, int]:
        """获取用户请求统计"""
        return {
            "minute": int(self._execute_with_retry(self.redis.get, self._get_key(phone, "minute")) or 0),
            "hour": int(self._execute_with_retry(self.redis.get, self._get_key(phone, "hour")) or 0),
            "day": int(self._execute_with_retry(self.redis.get, self._get_key(phone, "day")) or 0),
            "is_blocked": self._is_blocked(phone)
        }

    def get_global_stats(self) -> Dict[str, int]:
        """获取全局请求统计"""
        return {
            "minute": int(self._execute_with_retry(self.redis.get, self._get_global_key("minute")) or 0),
            "hour": int(self._execute_with_retry(self.redis.get, self._get_global_key("hour")) or 0),
            "day": int(self._execute_with_retry(self.redis.get, self._get_global_key("day")) or 0)
        }

# 创建全局实例
rate_limit_service = RateLimitService() 