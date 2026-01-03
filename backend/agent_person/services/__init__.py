"""服务层"""
from .brain_client import get_brain_client
from .asr_service import get_asr_service
from .tts_service import get_tts_service
from .digital_human_service import get_digital_human_service

__all__ = [
    "get_brain_client",
    "get_asr_service",
    "get_tts_service",
    "get_digital_human_service",
]
