"""
PocketSpeak 语音交互路由模块

提供语音会话管理、录音控制、文本发送等API接口
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime

# 导入语音会话管理器
from services.voice_chat.voice_session_manager import (
    get_voice_session,
    initialize_voice_session,
    close_voice_session,
    SessionState,
    SessionConfig,
    VoiceMessage
)
from services.device_lifecycle import PocketSpeakDeviceLifecycle, PocketSpeakDeviceManager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/voice", tags=["Voice Chat"])

# 全局设备管理器实例
_device_lifecycle_manager: Optional[PocketSpeakDeviceLifecycle] = None
_device_manager: Optional[PocketSpeakDeviceManager] = None


def initialize_device_managers():
    """初始化设备管理器"""
    global _device_lifecycle_manager, _device_manager

    if _device_lifecycle_manager is None:
        _device_lifecycle_manager = PocketSpeakDeviceLifecycle()
        logger.info("设备生命周期管理器已初始化")

    if _device_manager is None:
        _device_manager = PocketSpeakDeviceManager(_device_lifecycle_manager)
        logger.info("设备管理器已初始化")


# ========== 请求/响应模型 ==========

class SessionInitRequest(BaseModel):
    """会话初始化请求"""
    auto_play_tts: bool = False  # 移动端应用应该在前端播放音频,后端不播放
    save_conversation: bool = True
    enable_echo_cancellation: bool = True


class VoiceResponse(BaseModel):
    """标准语音响应模型"""
    success: bool
    message: str
    data: Dict[str, Any] = {}


class SendTextRequest(BaseModel):
    """发送文本消息请求"""
    text: str


class VoiceMessageResponse(BaseModel):
    """语音消息响应模型"""
    message_id: str
    timestamp: str
    user_text: Optional[str] = None
    ai_text: Optional[str] = None
    has_audio: bool = False


# ========== API端点 ==========

@router.post("/session/init", response_model=VoiceResponse)
async def initialize_session(
    request: SessionInitRequest,
    background_tasks: BackgroundTasks
):
    """
    初始化语音会话

    功能：
    1. 检查设备激活状态
    2. 初始化语音会话管理器
    3. 建立WebSocket连接
    4. 初始化录音和播放模块

    Returns:
        VoiceResponse: 操作结果
    """
    try:
        logger.info("🚀 开始初始化语音会话...")

        # 初始化设备管理器
        initialize_device_managers()

        # 检查设备激活状态
        if not _device_manager.check_activation_status():
            logger.warning("设备未激活，无法初始化语音会话")
            return VoiceResponse(
                success=False,
                message="设备未激活，请先完成设备激活流程",
                data={"activated": False}
            )

        # 创建会话配置
        logger.info(f"📋 收到的初始化参数: auto_play_tts={request.auto_play_tts}, save_conversation={request.save_conversation}, enable_echo_cancellation={request.enable_echo_cancellation}")
        session_config = SessionConfig(
            auto_play_tts=request.auto_play_tts,
            save_conversation=request.save_conversation,
            enable_echo_cancellation=request.enable_echo_cancellation
        )
        logger.info(f"📋 创建的会话配置: auto_play_tts={session_config.auto_play_tts}")

        # 检查是否已有会话
        session = get_voice_session()
        if session and session.is_initialized:
            # 输出旧会话配置用于调试
            logger.warning(f"⚠️ 发现已有会话! 旧配置: auto_play_tts={session.config.auto_play_tts}, 新配置: auto_play_tts={session_config.auto_play_tts}")

            # 检查配置是否相同
            if (session.config.auto_play_tts == session_config.auto_play_tts and
                session.config.save_conversation == session_config.save_conversation and
                session.config.enable_echo_cancellation == session_config.enable_echo_cancellation):
                logger.info("语音会话已存在且配置相同，复用现有会话")
                return VoiceResponse(
                    success=True,
                    message="语音会话已就绪",
                    data={
                        "session_id": session.session_id,
                        "state": session.state.value,
                        "stats": session.get_session_stats()
                    }
                )
            else:
                # 配置不同，关闭旧会话
                logger.warning("⚠️ 检测到配置变更，关闭旧会话并重新初始化")
                await close_voice_session()

        # 初始化语音会话
        success = await initialize_voice_session(_device_manager, session_config)

        if success:
            session = get_voice_session()
            return VoiceResponse(
                success=True,
                message="语音会话初始化成功",
                data={
                    "session_id": session.session_id,
                    "state": session.state.value,
                    "websocket_connected": session.ws_client.state.value,
                    "recorder_ready": session.recorder.is_initialized,
                    "player_ready": session.player.is_initialized
                }
            )
        else:
            return VoiceResponse(
                success=False,
                message="语音会话初始化失败，请查看日志获取详细信息",
                data={}
            )

    except Exception as e:
        error_msg = f"初始化语音会话时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.post("/session/close", response_model=VoiceResponse)
async def close_session():
    """
    关闭语音会话

    功能：
    1. 停止录音和播放
    2. 断开WebSocket连接
    3. 释放所有资源

    Returns:
        VoiceResponse: 操作结果
    """
    try:
        logger.info("🔚 关闭语音会话...")

        session = get_voice_session()
        if not session:
            return VoiceResponse(
                success=True,
                message="语音会话不存在或已关闭",
                data={}
            )

        # 获取会话统计信息
        stats = session.get_session_stats()

        # 关闭会话
        await close_voice_session()

        return VoiceResponse(
            success=True,
            message="语音会话已关闭",
            data={"final_stats": stats}
        )

    except Exception as e:
        error_msg = f"关闭语音会话时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.get("/session/status", response_model=VoiceResponse)
async def get_session_status():
    """
    获取语音会话状态

    Returns:
        VoiceResponse: 会话状态信息
    """
    try:
        session = get_voice_session()

        if not session:
            return VoiceResponse(
                success=False,
                message="语音会话未初始化",
                data={"initialized": False}
            )

        return VoiceResponse(
            success=True,
            message="会话状态正常",
            data={
                "initialized": session.is_initialized,
                "session_id": session.session_id,
                "state": session.state.value,
                "websocket_state": session.ws_client.state.value,
                "is_recording": session.recorder.is_recording,
                "is_playing": session.player.is_playing(),
                "stats": session.get_session_stats()
            }
        )

    except Exception as e:
        error_msg = f"获取会话状态时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.post("/recording/start", response_model=VoiceResponse)
async def start_recording():
    """
    开始录音并发送到AI

    功能：
    1. 开始录音
    2. 实时OPUS编码
    3. 通过WebSocket发送音频到AI

    Returns:
        VoiceResponse: 操作结果
    """
    try:
        logger.info("🎤 开始录音...")

        session = get_voice_session()
        if not session or not session.is_initialized:
            return VoiceResponse(
                success=False,
                message="语音会话未初始化，请先初始化会话",
                data={}
            )

        # 开始监听
        success = await session.start_listening()

        if success:
            return VoiceResponse(
                success=True,
                message="开始录音",
                data={
                    "state": session.state.value,
                    "is_recording": session.recorder.is_recording
                }
            )
        else:
            return VoiceResponse(
                success=False,
                message="无法开始录音，请检查会话状态",
                data={"state": session.state.value}
            )

    except Exception as e:
        error_msg = f"开始录音时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.post("/recording/stop", response_model=VoiceResponse)
async def stop_recording():
    """
    停止录音

    功能：
    1. 停止录音
    2. 等待AI处理和响应

    Returns:
        VoiceResponse: 操作结果
    """
    try:
        logger.info("⏹️ 停止录音...")

        session = get_voice_session()
        if not session or not session.is_initialized:
            return VoiceResponse(
                success=False,
                message="语音会话未初始化",
                data={}
            )

        # 停止监听
        success = await session.stop_listening()

        if success:
            return VoiceResponse(
                success=True,
                message="停止录音，等待AI响应",
                data={
                    "state": session.state.value,
                    "is_recording": session.recorder.is_recording
                }
            )
        else:
            return VoiceResponse(
                success=False,
                message="停止录音失败",
                data={"state": session.state.value}
            )

    except Exception as e:
        error_msg = f"停止录音时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.post("/message/send", response_model=VoiceResponse)
async def send_text_message(request: SendTextRequest):
    """
    发送文本消息到AI

    Args:
        request: 包含文本内容的请求

    Returns:
        VoiceResponse: 操作结果
    """
    try:
        logger.info(f"💬 发送文本消息: {request.text}")

        session = get_voice_session()
        if not session or not session.is_initialized:
            return VoiceResponse(
                success=False,
                message="语音会话未初始化",
                data={}
            )

        # 发送文本消息
        success = await session.send_text_message(request.text)

        if success:
            return VoiceResponse(
                success=True,
                message="文本消息已发送",
                data={
                    "text": request.text,
                    "state": session.state.value
                }
            )
        else:
            return VoiceResponse(
                success=False,
                message="发送文本消息失败",
                data={}
            )

    except Exception as e:
        error_msg = f"发送文本消息时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.get("/conversation/history")
async def get_conversation_history(limit: int = 50):
    """
    获取对话历史记录

    Args:
        limit: 返回的最大消息数量

    Returns:
        对话历史列表
    """
    try:
        session = get_voice_session()
        if not session:
            return {
                "success": False,
                "message": "语音会话未初始化",
                "data": {"messages": []}
            }

        history = session.get_conversation_history()

        # 限制返回数量
        if len(history) > limit:
            history = history[-limit:]

        # 转换为可序列化格式
        messages = []
        for msg in history:
            message_dict = {
                "message_id": msg.message_id,
                "timestamp": msg.timestamp.isoformat(),
                "user_text": msg.user_text,
                "ai_text": msg.ai_text,
                "has_audio": msg.ai_audio is not None,
                "message_type": msg.message_type.value if msg.message_type else None
            }

            # 如果有音频数据，转换为WAV格式
            if msg.ai_audio:
                import base64
                import wave
                import io

                try:
                    # 如果已经是PCM格式,直接封装为WAV
                    if msg.ai_audio.format == "pcm":
                        pcm_data = msg.ai_audio.data
                        logger.info(f"📦 使用已解码的PCM数据: {len(pcm_data)} bytes, 格式={msg.ai_audio.format}, sample_rate={msg.ai_audio.sample_rate}, channels={msg.ai_audio.channels}")
                    else:
                        # 其他格式(如OPUS)需要先解码
                        import opuslib
                        decoder = opuslib.Decoder(msg.ai_audio.sample_rate, msg.ai_audio.channels)
                        pcm_data = decoder.decode(msg.ai_audio.data, frame_size=960, decode_fec=False)
                        logger.info(f"🔄 OPUS解码为PCM: {len(msg.ai_audio.data)} bytes (OPUS) → {len(pcm_data)} bytes (PCM)")

                    # 将PCM数据封装为WAV格式
                    wav_buffer = io.BytesIO()
                    with wave.open(wav_buffer, 'wb') as wav_file:
                        wav_file.setnchannels(msg.ai_audio.channels)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(msg.ai_audio.sample_rate)
                        wav_file.writeframes(pcm_data)

                    wav_data = wav_buffer.getvalue()

                    message_dict["audio_data"] = base64.b64encode(wav_data).decode('utf-8')
                    message_dict["audio_format"] = "wav"
                    message_dict["audio_sample_rate"] = msg.ai_audio.sample_rate
                    message_dict["audio_channels"] = msg.ai_audio.channels

                    logger.info(f"✅ 音频转WAV成功: {len(pcm_data)} bytes (PCM) → {len(wav_data)} bytes (WAV), 参数: {msg.ai_audio.sample_rate}Hz, {msg.ai_audio.channels}ch")
                except Exception as e:
                    logger.error(f"❌ 音频转WAV失败: {e}")
                    # 失败时仍返回原始数据
                    message_dict["audio_data"] = base64.b64encode(msg.ai_audio.data).decode('utf-8')
                    message_dict["audio_format"] = msg.ai_audio.format
                    message_dict["audio_sample_rate"] = msg.ai_audio.sample_rate
                    message_dict["audio_channels"] = msg.ai_audio.channels

            messages.append(message_dict)

        return {
            "success": True,
            "message": f"获取到 {len(messages)} 条历史消息",
            "data": {
                "messages": messages,
                "total_count": len(session.conversation_history)
            }
        }

    except Exception as e:
        error_msg = f"获取对话历史时发生错误: {e}"
        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.get("/conversation/sentences")
async def get_completed_sentences(last_sentence_index: int = 0):
    """
    获取已完成的句子及其音频（用于逐句播放）

    Args:
        last_sentence_index: 前端已获取到的句子索引

    Returns:
        已完成的句子列表
    """
    try:
        session = get_voice_session()
        if not session:
            return {
                "success": False,
                "message": "语音会话未初始化",
                "data": {
                    "has_new_sentences": False,
                    "is_complete": False
                }
            }

        current_message = session.current_message
        if not current_message:
            return {
                "success": True,
                "message": "当前没有进行中的对话",
                "data": {
                    "has_new_sentences": False,
                    "total_sentences": 0,
                    "is_complete": False
                }
            }

        # 获取已完成的句子
        result = current_message.get_completed_sentences(last_sentence_index)

        if result["has_new_sentences"]:
            logger.info(f"🎵 返回新完成的句子: {len(result['sentences'])}句, 总计{result['total_sentences']}句, 完成={result['is_complete']}")

        return {
            "success": True,
            "message": "获取句子成功",
            "data": result
        }

    except Exception as e:
        logger.error(f"获取句子失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "data": {
                "has_new_sentences": False,
                "is_complete": False
            }
        }


@router.get("/conversation/incremental-audio")
async def get_incremental_audio(last_chunk_index: int = 0):
    """
    获取当前对话的增量音频数据（用于流式播放）

    Args:
        last_chunk_index: 前端已获取到的音频块索引

    Returns:
        增量音频数据
    """
    try:
        session = get_voice_session()
        if not session:
            return {
                "success": False,
                "message": "语音会话未初始化",
                "data": {
                    "has_new_audio": False,
                    "is_complete": False
                }
            }

        # 获取当前消息
        current_message = session.current_message
        if not current_message:
            return {
                "success": True,
                "message": "当前没有进行中的对话",
                "data": {
                    "has_new_audio": False,
                    "is_complete": False
                }
            }

        # 获取增量音频
        audio_info = current_message.get_incremental_audio(last_chunk_index)

        # 如果有新音频，需要将PCM封装为WAV格式
        if audio_info.get("has_new_audio"):
            import base64
            import wave
            import io

            try:
                # 解码Base64得到PCM数据
                pcm_data = base64.b64decode(audio_info["audio_data"])

                # 将PCM封装为WAV格式
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(audio_info["channels"])
                    wav_file.setsampwidth(2)  # 16-bit PCM
                    wav_file.setframerate(audio_info["sample_rate"])
                    wav_file.writeframes(pcm_data)

                wav_data = wav_buffer.getvalue()
                wav_base64 = base64.b64encode(wav_data).decode('utf-8')

                logger.info(
                    f"🎵 返回增量音频: chunk_index {last_chunk_index}→{audio_info['chunk_count']}, "
                    f"新增 {audio_info['new_audio_size']} bytes, "
                    f"总计 {audio_info['total_audio_size']} bytes PCM → {len(wav_data)} bytes WAV, "
                    f"完成={audio_info['is_complete']}"
                )

                return {
                    "success": True,
                    "message": "获取增量音频成功",
                    "data": {
                        "has_new_audio": True,
                        "audio_data": wav_base64,
                        "chunk_count": audio_info["chunk_count"],
                        "is_complete": audio_info["is_complete"],
                        "new_audio_size": audio_info["new_audio_size"],
                        "total_audio_size": audio_info["total_audio_size"]
                    }
                }

            except Exception as e:
                logger.error(f"封装WAV格式失败: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"音频处理失败: {e}",
                    "data": {
                        "has_new_audio": False,
                        "is_complete": audio_info.get("is_complete", False)
                    }
                }

        # 没有新音频
        return {
            "success": True,
            "message": "当前没有新音频",
            "data": {
                "has_new_audio": False,
                "chunk_count": audio_info["chunk_count"],
                "is_complete": audio_info["is_complete"]
            }
        }

    except Exception as e:
        error_msg = f"获取增量音频失败: {e}"
        logger.error(error_msg, exc_info=True)

        return {
            "success": False,
            "message": error_msg,
            "data": {
                "has_new_audio": False,
                "is_complete": False
            }
        }


@router.get("/health")
async def voice_health_check():
    """
    语音系统健康检查

    Returns:
        健康状态信息
    """
    try:
        session = get_voice_session()

        if not session:
            return {
                "healthy": False,
                "message": "语音会话未初始化",
                "components": {
                    "session": False,
                    "websocket": False,
                    "recorder": False,
                    "player": False
                }
            }

        is_healthy = (
            session.is_initialized and
            session.state not in [SessionState.ERROR, SessionState.CLOSED] and
            session.ws_client.state.value == "authenticated"
        )

        return {
            "healthy": is_healthy,
            "message": "语音系统健康" if is_healthy else "语音系统存在问题",
            "components": {
                "session": session.is_initialized,
                "websocket": session.ws_client.state.value == "authenticated",
                "recorder": session.recorder.is_initialized,
                "player": session.player.is_initialized
            },
            "state": session.state.value,
            "stats": session.get_session_stats()
        }

    except Exception as e:
        logger.error(f"语音健康检查异常: {e}")
        return {
            "healthy": False,
            "message": f"健康检查失败: {e}",
            "components": {
                "session": False,
                "websocket": False,
                "recorder": False,
                "player": False
            }
        }


# ========== WebSocket实时通信端点 ==========

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点用于实时语音交互

    功能：
    1. 接收前端发送的录音数据
    2. 推送AI响应到前端
    3. 实时状态同步
    """
    await websocket.accept()
    logger.info("WebSocket客户端已连接")

    try:
        session = get_voice_session()
        if not session or not session.is_initialized:
            await websocket.send_json({
                "type": "error",
                "message": "语音会话未初始化"
            })
            await websocket.close()
            return

        # 🚀 设置回调函数推送消息到前端（完全模仿py-xiaozhi）
        def on_user_text_received(text: str):
            """收到用户语音识别文字立即推送"""
            logger.info(f"📝 推送用户文字: {text}")
            asyncio.create_task(websocket.send_json({
                "type": "user_text",
                "data": text
            }))

        def on_text_received(text: str):
            """收到AI文本立即推送"""
            # ✅ 保留关键文本日志（低频）
            logger.info(f"📝 推送AI文本: {text}")
            asyncio.create_task(websocket.send_json({
                "type": "text",
                "data": text
            }))

        def on_state_change(state):
            """状态变化推送"""
            # ✅ 保留关键状态日志（低频）
            logger.debug(f"🔄 状态变化: {state.value}")
            asyncio.create_task(websocket.send_json({
                "type": "state_change",
                "data": {"state": state.value}
            }))

        def on_audio_frame(audio_data: bytes):
            """收到音频帧立即推送（模仿py-xiaozhi的即时播放）"""
            import base64
            try:
                # 🔥 关键修复：使用 run_coroutine_threadsafe 确保任务真正执行
                loop = asyncio.get_event_loop()

                async def _send():
                    try:
                        await websocket.send_json({
                            "type": "audio_frame",
                            "data": base64.b64encode(audio_data).decode('utf-8')
                        })
                        logger.debug(f"✅ 音频帧已推送: {len(audio_data)} bytes")
                    except Exception as e:
                        logger.error(f"❌ WebSocket发送音频帧失败: {e}")

                asyncio.run_coroutine_threadsafe(_send(), loop)
            except Exception as e:
                logger.error(f"❌ on_audio_frame 回调失败: {e}", exc_info=True)

        # 🚀 注册回调（纯WebSocket推送，无轮询）
        session.on_user_speech_end = on_user_text_received  # 用户文字推送
        session.on_text_received = on_text_received  # AI文本推送
        session.on_state_changed = on_state_change  # 状态推送
        session.on_audio_frame_received = on_audio_frame  # 音频帧推送

        # 保持连接并处理消息
        while True:
            data = await websocket.receive()

            if "text" in data:
                message = data["text"]
                # 处理文本命令
                logger.info(f"收到WebSocket文本消息: {message}")

            elif "bytes" in data:
                # 处理音频数据
                audio_data = data["bytes"]
                logger.debug(f"收到WebSocket音频数据: {len(audio_data)} bytes")

    except WebSocketDisconnect:
        logger.info("WebSocket客户端已断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)
    finally:
        logger.info("WebSocket连接已关闭")


# ========== 启动和关闭事件 ==========

@router.on_event("startup")
async def startup_event():
    """应用启动事件处理"""
    logger.info("语音交互路由模块启动")
    initialize_device_managers()


@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件处理"""
    logger.info("语音交互路由模块关闭")

    try:
        # 关闭语音会话
        await close_voice_session()
        logger.info("语音会话已在应用关闭时释放")
    except Exception as e:
        logger.error(f"关闭语音会话时发生错误: {e}")
