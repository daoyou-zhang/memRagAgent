"""聊天 API

支持文本、语音、数字人多模态交互
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from ..models.chat import ChatRequest, ChatResponse, VoiceMessage
from ..services import get_brain_client, get_asr_service, get_tts_service, get_digital_human_service


router = APIRouter()


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str, 
    limit: int = 50,
    offset: int = 0
):
    """获取聊天历史（分页）
    
    Args:
        session_id: 会话 ID
        limit: 每页数量（默认 50）
        offset: 偏移量（默认 0）
    
    Returns:
        {
            "session_id": str,
            "messages": [{"role": str, "content": str, "timestamp": str}],
            "total": int,
            "has_more": bool
        }
    """
    try:
        brain_client = get_brain_client()
        
        # TODO: 实现从 memory 系统获取历史的接口
        # 目前返回模拟数据用于测试
        
        logger.info(f"获取聊天历史: session_id={session_id}, limit={limit}, offset={offset}")
        
        # 模拟数据（实际应该从 memory 系统获取）
        all_messages = []  # TODO: 从 memory 获取
        total = len(all_messages)
        
        # 分页
        start = offset
        end = offset + limit
        messages = all_messages[start:end]
        has_more = end < total
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total": total,
            "has_more": has_more,
            "offset": offset,
            "limit": limit
        }
    except Exception as exc:
        logger.error(f"获取聊天历史失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/text", response_model=ChatResponse)
async def chat_text(request: ChatRequest):
    """文本聊天
    
    基础的文本对话，可选返回语音和数字人视频
    """
    start_time = datetime.now()
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # 1. 调用认知大脑
        brain_client = get_brain_client()
        brain_response = await brain_client.process(
            user_input=request.input,
            user_id=request.user_id,
            session_id=session_id,
            project_id=request.project_id,
            stream=False,
        )
        
        content = brain_response.get("content", "")
        
        # 2. 如果需要语音，调用 TTS
        audio_url = None
        if request.enable_voice and content:
            tts_service = get_tts_service()
            try:
                audio_data = await tts_service.synthesize(
                    text=content,
                    voice=request.voice_config.get("voice") if request.voice_config else None,
                )
                # TODO: 保存音频文件并返回 URL
                audio_url = None  # 临时
            except Exception as exc:
                logger.warning(f"TTS 合成失败: {exc}")
        
        # 3. 如果需要数字人，调用数字人服务
        video_url = None
        if request.enable_digital_human and content:
            dh_service = get_digital_human_service()
            try:
                dh_result = await dh_service.generate_video(text=content)
                video_url = dh_result.get("video_url")
            except Exception as exc:
                logger.warning(f"数字人生成失败: {exc}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ChatResponse(
            content=content,
            session_id=session_id,
            audio_url=audio_url,
            video_url=video_url,
            processing_time=processing_time,
        )
    
    except Exception as exc:
        logger.error(f"聊天处理失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/voice")
async def chat_voice(voice_message: VoiceMessage, user_id: str, session_id: Optional[str] = None):
    """语音聊天
    
    接收语音输入，返回文本和语音回复
    """
    session_id = session_id or str(uuid.uuid4())
    
    try:
        # 1. ASR 识别
        asr_service = get_asr_service()
        text = await asr_service.recognize(
            audio_data=voice_message.audio_data,
            format=voice_message.format,
            sample_rate=voice_message.sample_rate,
        )
        
        # 2. 调用文本聊天
        request = ChatRequest(
            input=text,
            user_id=user_id,
            session_id=session_id,
            enable_voice=True,
        )
        
        return await chat_text(request)
    
    except Exception as exc:
        logger.error(f"语音聊天失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """WebSocket 实时聊天
    
    支持双向实时通信，适合数字人实时交互
    """
    await websocket.accept()
    session_id = None  # 将从客户端接收
    
    logger.info(f"WebSocket 连接建立")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            message_type = data.get("type", "text")
            user_id = data.get("user_id", "anonymous")
            
            # 获取或使用客户端提供的 session_id
            if not session_id:
                session_id = data.get("session_id") or str(uuid.uuid4())
                logger.info(f"使用 session_id: {session_id}")
            
            if message_type == "text":
                # 文本消息
                user_input = data.get("input", "")
                logger.info(f"收到文本消息: user_id={user_id}, input={user_input}")
                
                # 调用认知大脑（流式）
                brain_client = get_brain_client()
                
                try:
                    # 使用流式处理
                    full_response = ""
                    async for chunk in brain_client.process_stream(
                        user_input=user_input,
                        user_id=user_id,
                        session_id=session_id,
                    ):
                        # chunk 是 SSE 格式的数据，需要解析
                        try:
                            import json
                            chunk_data = json.loads(chunk)
                            
                            # 提取文本内容
                            if "text" in chunk_data:
                                text = chunk_data["text"]
                                full_response += text
                                
                                # 发送给前端
                                await websocket.send_json({
                                    "type": "content",
                                    "data": {"text": text},
                                })
                            elif "content" in chunk_data:
                                text = chunk_data["content"]
                                full_response += text
                                
                                await websocket.send_json({
                                    "type": "content",
                                    "data": {"text": text},
                                })
                        except json.JSONDecodeError:
                            # 如果不是 JSON，直接作为文本发送
                            full_response += chunk
                            await websocket.send_json({
                                "type": "content",
                                "data": {"text": chunk},
                            })
                    
                    logger.info(f"回复完成: {full_response[:100]}...")
                    
                    # 发送完成信号
                    await websocket.send_json({
                        "type": "done",
                        "session_id": session_id,
                    })
                except Exception as exc:
                    logger.error(f"处理消息失败: {exc}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "error": str(exc),
                    })
            
            elif message_type == "voice":
                # 语音消息
                # TODO: 实现语音处理
                pass
            
            elif message_type == "ping":
                # 心跳
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接断开: session_id={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket 错误: {exc}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass
