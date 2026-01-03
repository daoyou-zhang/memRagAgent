"""语音识别服务（ASR）

使用阿里云 DashScope Qwen3-ASR-Flash
"""
import os
from typing import Optional
import httpx
from loguru import logger


class ASRService:
    """语音识别服务"""
    
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.api_base = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/api/v1")
        self.model = os.getenv("DASHSCOPE_API_MODEL", "qwen3-asr-flash")
        
        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY 未配置，ASR 功能将不可用")
        
        logger.info(f"ASR 服务初始化: model={self.model}")
    
    async def recognize(
        self,
        audio_data: bytes,
        format: str = "pcm",
        sample_rate: int = 16000,
        language: str = "zh",
    ) -> str:
        """识别语音
        
        Args:
            audio_data: 音频数据
            format: 音频格式（pcm/wav/mp3）
            sample_rate: 采样率
            language: 语言（zh/en）
        
        Returns:
            识别的文本
        """
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")
        
        # TODO: 实现阿里云 ASR API 调用
        # 这里需要根据阿里云 DashScope 的实际 API 文档实现
        
        logger.info(f"ASR 识别: format={format}, sample_rate={sample_rate}, size={len(audio_data)} bytes")
        
        # 临时返回占位符
        return "[ASR 识别结果占位符]"
    
    async def recognize_stream(
        self,
        audio_stream,
        format: str = "pcm",
        sample_rate: int = 16000,
    ):
        """流式识别语音"""
        # TODO: 实现流式 ASR
        pass


# 单例
_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """获取 ASR 服务单例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
