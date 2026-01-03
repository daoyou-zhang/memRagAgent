"""语音 API

语音识别和合成的独立接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from loguru import logger

from ..services import get_asr_service, get_tts_service


router = APIRouter()


@router.post("/asr")
async def speech_to_text(
    audio: UploadFile = File(...),
    format: str = "wav",
    language: str = "zh",
):
    """语音识别（ASR）
    
    将语音转换为文本
    """
    try:
        audio_data = await audio.read()
        
        asr_service = get_asr_service()
        text = await asr_service.recognize(
            audio_data=audio_data,
            format=format,
            language=language,
        )
        
        return {
            "text": text,
            "language": language,
            "audio_size": len(audio_data),
        }
    
    except Exception as exc:
        logger.error(f"ASR 失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tts")
async def text_to_speech(
    text: str,
    voice: str = "xiaoyun",
    format: str = "mp3",
):
    """语音合成（TTS）
    
    将文本转换为语音
    """
    try:
        tts_service = get_tts_service()
        audio_data = await tts_service.synthesize(
            text=text,
            voice=voice,
            format=format,
        )
        
        # 返回音频文件
        media_type = f"audio/{format}"
        return Response(content=audio_data, media_type=media_type)
    
    except Exception as exc:
        logger.error(f"TTS 失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
