"""
PocketSpeak 语音会话管理器

整合WebSocket连接、语音录制、AI响应解析和TTS播放模块
提供完整的语音交互会话管理功能
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# 导入语音通信模块
from services.voice_chat.ws_client import XiaozhiWebSocketClient, ConnectionState, WSConfig
from services.voice_chat.speech_recorder import SpeechRecorder, RecordingConfig
from services.voice_chat.ai_response_parser import AIResponseParser, AIResponse, MessageType, AudioData
from services.voice_chat.tts_player import TTSPlayer, PlaybackConfig, TTSRequest

# 导入设备管理
from services.device_lifecycle import PocketSpeakDeviceManager

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """会话状态枚举"""
    IDLE = "idle"                       # 空闲状态
    INITIALIZING = "initializing"       # 初始化中
    READY = "ready"                     # 就绪状态
    LISTENING = "listening"             # 正在监听用户语音
    PROCESSING = "processing"           # 正在处理AI响应
    SPEAKING = "speaking"               # AI正在说话
    ERROR = "error"                     # 错误状态
    CLOSED = "closed"                   # 会话已关闭


@dataclass
class VoiceMessage:
    """语音消息数据结构"""
    message_id: str
    timestamp: datetime
    user_text: Optional[str] = None
    ai_text: Optional[str] = None
    ai_audio: Optional[AudioData] = None
    message_type: Optional[MessageType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _pcm_chunks: List[bytes] = field(default_factory=list)  # 累积PCM数据块(已解码)
    _sample_rate: int = 24000
    _channels: int = 1
    _opus_decoder: Optional[Any] = field(default=None, init=False, repr=False)  # 复用的OPUS解码器(参考py-xiaozhi标准实现)

    def append_audio_chunk(self, audio_data: AudioData):
        """
        累积音频数据块 - 先解码OPUS为PCM再累积

        优化说明（参考py-xiaozhi标准实现）:
        1. 复用OPUS解码器实例，避免每帧都创建新解码器
        2. 解码失败时跳过该帧，避免引入脏数据
        """
        import opuslib

        try:
            # 如果是OPUS格式,先解码为PCM
            if audio_data.format == "opus":
                # 初始化或复用解码器（参考py-xiaozhi的self.opus_decoder模式）
                if self._opus_decoder is None:
                    self._opus_decoder = opuslib.Decoder(audio_data.sample_rate, audio_data.channels)
                    self._sample_rate = audio_data.sample_rate
                    self._channels = audio_data.channels

                # 使用960帧大小解码(24kHz下40ms的帧，与py-xiaozhi一致)
                pcm_data = self._opus_decoder.decode(audio_data.data, frame_size=960, decode_fec=False)
                self._pcm_chunks.append(pcm_data)

                # 合并所有PCM块（注意：这里必须合并，因为前端需要完整音频）
                merged_pcm = b''.join(self._pcm_chunks)
                self.ai_audio = AudioData(
                    data=merged_pcm,
                    format="pcm",
                    sample_rate=self._sample_rate,
                    channels=self._channels
                )
            else:
                # 非OPUS格式直接累积
                self._pcm_chunks.append(audio_data.data)
                merged_data = b''.join(self._pcm_chunks)
                self.ai_audio = AudioData(
                    data=merged_data,
                    format=audio_data.format,
                    sample_rate=audio_data.sample_rate,
                    channels=audio_data.channels
                )
        except opuslib.OpusError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Opus解码失败，跳过此帧: {e}")
            # 解码失败时跳过该帧（参考py-xiaozhi的错误处理）
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"音频处理失败，跳过此帧: {e}")


@dataclass
class SessionConfig:
    """会话配置"""
    auto_play_tts: bool = False         # 后端不自动播放TTS（音频由前端播放）
    save_conversation: bool = True       # 保存对话记录
    max_conversation_history: int = 100  # 最大对话历史条数
    listening_timeout: float = 5.0       # 监听超时时间（秒）
    enable_echo_cancellation: bool = True # 启用回声消除


class VoiceSessionManager:
    """
    语音会话管理器

    功能：
    1. 整合WebSocket连接、录音、解析、播放模块
    2. 管理语音交互的完整生命周期
    3. 处理用户语音输入和AI语音输出
    4. 维护对话历史记录
    5. 提供会话状态管理和事件回调
    """

    def __init__(
        self,
        device_manager: PocketSpeakDeviceManager,
        session_config: Optional[SessionConfig] = None,
        ws_config: Optional[WSConfig] = None,
        recording_config: Optional[RecordingConfig] = None,
        playback_config: Optional[PlaybackConfig] = None
    ):
        """
        初始化语音会话管理器

        Args:
            device_manager: 设备管理器实例
            session_config: 会话配置
            ws_config: WebSocket配置
            recording_config: 录音配置
            playback_config: 播放配置
        """
        self.device_manager = device_manager
        self.config = session_config or SessionConfig()

        # 初始化各个子模块
        self.ws_client = XiaozhiWebSocketClient(ws_config, device_manager)
        self.recorder = SpeechRecorder(recording_config)
        self.parser = AIResponseParser()
        self.player = TTSPlayer(playback_config)

        # 会话状态
        self.state = SessionState.IDLE
        self.session_id: Optional[str] = None
        self.is_initialized = False

        # 事件循环引用（用于跨线程提交异步任务）
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # 对话历史
        self.conversation_history: List[VoiceMessage] = []
        self.current_message: Optional[VoiceMessage] = None

        # 回调函数
        self.on_session_ready: Optional[Callable[[], None]] = None
        self.on_user_speech_start: Optional[Callable[[], None]] = None
        self.on_user_speech_end: Optional[Callable[[str], None]] = None
        self.on_ai_response_received: Optional[Callable[[AIResponse], None]] = None
        self.on_ai_speaking_start: Optional[Callable[[], None]] = None
        self.on_ai_speaking_end: Optional[Callable[[], None]] = None
        self.on_session_error: Optional[Callable[[str], None]] = None
        self.on_state_changed: Optional[Callable[[SessionState], None]] = None

        # 统计信息
        self.stats = {
            "total_messages": 0,
            "total_user_speech_time": 0.0,
            "total_ai_response_time": 0.0,
            "session_start_time": None,
            "session_uptime": 0.0
        }

        logger.info("VoiceSessionManager 初始化完成")

    async def initialize(self) -> bool:
        """
        初始化会话管理器和所有子模块

        Returns:
            bool: 初始化是否成功
        """
        if self.is_initialized:
            logger.warning("会话管理器已经初始化")
            return True

        try:
            logger.info("🚀 开始初始化语音会话管理器...")
            self._update_state(SessionState.INITIALIZING)

            # 0. 保存事件循环引用
            self._loop = asyncio.get_running_loop()
            logger.info(f"✅ 事件循环已保存: {self._loop}")

            # 1. 检查设备激活状态
            if not self.device_manager.check_activation_status():
                error_msg = "设备未激活，无法初始化语音会话"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 2. 获取连接参数
            device_info = self.device_manager.lifecycle_manager.load_device_info_from_local()
            if not device_info:
                error_msg = "无法获取设备信息"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 直接访问connection_params属性
            connection_params = getattr(device_info, 'connection_params', {})
            websocket_params = connection_params.get('websocket', {})

            if not websocket_params:
                error_msg = "设备连接参数中缺少WebSocket配置"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 3. 更新WebSocket配置
            ws_url = websocket_params.get('url', 'wss://api.tenclass.net/xiaozhi/v1/')
            self.ws_client.config.url = ws_url
            logger.info(f"✅ WebSocket URL: {ws_url}")

            # 4. 初始化录音模块
            logger.info("初始化语音录制模块...")
            if not await self.recorder.initialize():
                error_msg = "语音录制模块初始化失败"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False
            logger.info("✅ 语音录制模块初始化成功")

            # 5. 初始化播放模块
            logger.info("初始化TTS播放模块...")
            if not await self.player.initialize():
                error_msg = "TTS播放模块初始化失败"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False
            logger.info("✅ TTS播放模块初始化成功")

            # 6. 设置回调函数
            self._setup_callbacks()

            # 7. 建立WebSocket连接
            logger.info("建立WebSocket连接...")
            if not await self.ws_client.connect():
                error_msg = "WebSocket连接失败"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False
            logger.info("✅ WebSocket连接建立成功")

            # 8. 等待认证完成
            await asyncio.sleep(2)  # 给认证过程一些时间

            if self.ws_client.state != ConnectionState.AUTHENTICATED:
                logger.warning(f"WebSocket认证状态: {self.ws_client.state.value}")

            # 9. 生成会话ID
            self.session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
            self.stats["session_start_time"] = datetime.now()

            self.is_initialized = True
            self._update_state(SessionState.READY)

            logger.info(f"🎉 语音会话管理器初始化完成 - Session ID: {self.session_id}")

            if self.on_session_ready:
                self.on_session_ready()

            return True

        except Exception as e:
            error_msg = f"初始化语音会话管理器失败: {e}"
            logger.error(error_msg, exc_info=True)
            self._trigger_error(error_msg)
            return False

    def _setup_callbacks(self):
        """设置各模块的回调函数"""
        # 录音模块回调
        self.recorder.on_audio_encoded = self._on_audio_encoded
        self.recorder.on_recording_started = self._on_recording_started
        self.recorder.on_recording_stopped = self._on_recording_stopped
        self.recorder.on_error = self._on_recorder_error

        # WebSocket客户端回调
        self.ws_client.on_message_received = self._on_ws_message_received
        self.ws_client.on_disconnected = self._on_ws_disconnected
        self.ws_client.on_error = self._on_ws_error

        # 解析器回调
        self.parser.on_text_received = self._on_text_received
        self.parser.on_audio_received = self._on_audio_received
        self.parser.on_mcp_received = self._on_mcp_received
        self.parser.on_tts_received = self._on_tts_received
        self.parser.on_error_received = self._on_parse_error

        # 播放器回调
        self.player.on_playback_started = self._on_playback_started
        self.player.on_playback_finished = self._on_playback_finished
        self.player.on_playback_error = self._on_playback_error

        logger.info("✅ 回调函数设置完成")

    async def start_listening(self) -> bool:
        """
        开始监听用户语音输入

        遵循py-xiaozhi协议：
        1. 先发送start_listening消息通知服务器
        2. 然后开始本地录音

        Returns:
            bool: 是否成功开始监听
        """
        if not self.is_initialized:
            logger.error("会话管理器未初始化，无法开始监听")
            return False

        if self.state not in [SessionState.READY, SessionState.SPEAKING]:
            logger.warning(f"当前状态 {self.state.value} 不适合开始监听")
            return False

        try:
            logger.info("🎤 开始监听用户语音...")

            # 步骤1：先发送开始监听消息到服务器（遵循py-xiaozhi协议）
            # 使用AUTO_STOP模式（回合制对话）
            mode = "auto"  # 可选: "auto"(回合制), "manual"(手动), "realtime"(实时)
            success = await self.ws_client.send_start_listening(mode)
            if not success:
                error_msg = "发送开始监听消息失败"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 步骤2：更新状态
            self._update_state(SessionState.LISTENING)

            # 步骤3：开始本地录音
            if not await self.recorder.start_recording():
                error_msg = "无法开始录音"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 步骤4：创建新的消息对象
            self.current_message = VoiceMessage(
                message_id=f"msg_{int(datetime.now().timestamp() * 1000)}",
                timestamp=datetime.now()
            )

            logger.info(f"✅ 监听已开始: mode={mode}")
            return True

        except Exception as e:
            error_msg = f"开始监听失败: {e}"
            logger.error(error_msg, exc_info=True)
            self._trigger_error(error_msg)
            return False

    async def stop_listening(self) -> bool:
        """
        停止监听用户语音输入

        遵循py-xiaozhi协议：
        1. 先停止本地录音
        2. 发送stop_listening消息通知服务器

        Returns:
            bool: 是否成功停止监听
        """
        # 允许在LISTENING或SPEAKING状态下停止录音
        # SPEAKING状态：用户可能在AI说话时点击停止按钮
        if self.state not in [SessionState.LISTENING, SessionState.SPEAKING]:
            logger.warning(f"当前状态 {self.state.value} 不需要停止监听")
            return False

        try:
            logger.info("⏹️ 停止监听用户语音...")

            # 步骤1：停止本地录音
            await self.recorder.stop_recording()

            # 步骤2：发送停止监听消息到服务器（遵循py-xiaozhi协议）
            success = await self.ws_client.send_stop_listening()
            if not success:
                logger.warning("发送停止监听消息失败，但本地录音已停止")

            # 步骤3：更新状态为处理中
            self._update_state(SessionState.PROCESSING)
            logger.info("✅ 停止监听，等待AI响应...")

            return True

        except Exception as e:
            error_msg = f"停止监听失败: {e}"
            logger.error(error_msg, exc_info=True)
            self._trigger_error(error_msg)
            return False

    async def send_text_message(self, text: str) -> bool:
        """
        发送文本消息到AI

        Args:
            text: 要发送的文本内容

        Returns:
            bool: 是否发送成功
        """
        if not self.is_initialized:
            logger.error("会话管理器未初始化，无法发送消息")
            return False

        try:
            logger.info(f"💬 发送文本消息: {text}")

            text_message = {
                "session_id": self.session_id,
                "type": "text",
                "content": text
            }
            await self.ws_client.send_message(text_message)

            # 创建消息记录
            message = VoiceMessage(
                message_id=f"msg_{int(datetime.now().timestamp() * 1000)}",
                timestamp=datetime.now(),
                user_text=text
            )
            self.current_message = message

            self._update_state(SessionState.PROCESSING)

            return True

        except Exception as e:
            error_msg = f"发送文本消息失败: {e}"
            logger.error(error_msg, exc_info=True)
            self._trigger_error(error_msg)
            return False

    async def close(self):
        """关闭会话管理器，释放所有资源"""
        logger.info("🔚 关闭语音会话管理器...")

        self._update_state(SessionState.CLOSED)

        try:
            # 停止录音
            if self.recorder.is_recording:
                await self.recorder.stop_recording()

            # 停止播放
            if self.player.is_playing():
                await self.player.stop()

            # 断开WebSocket连接
            if self.ws_client.state != ConnectionState.DISCONNECTED:
                await self.ws_client.disconnect()

            # 清理资源
            await self.recorder.cleanup()
            await self.player.cleanup()

            self.is_initialized = False
            logger.info("✅ 语音会话管理器已关闭")

        except Exception as e:
            logger.error(f"关闭会话管理器时发生错误: {e}", exc_info=True)

    def get_conversation_history(self) -> List[VoiceMessage]:
        """获取对话历史记录"""
        return self.conversation_history.copy()

    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        stats = self.stats.copy()
        if stats["session_start_time"]:
            stats["session_uptime"] = (datetime.now() - stats["session_start_time"]).total_seconds()
        return stats

    def _update_state(self, new_state: SessionState):
        """更新会话状态"""
        old_state = self.state
        self.state = new_state
        logger.info(f"会话状态变更: {old_state.value} -> {new_state.value}")

        if self.on_state_changed:
            self.on_state_changed(new_state)

    def _trigger_error(self, error_message: str):
        """触发错误回调"""
        self._update_state(SessionState.ERROR)
        if self.on_session_error:
            self.on_session_error(error_message)

    # ========== 录音模块回调 ==========

    def _on_audio_encoded(self, audio_data: bytes):
        """
        当音频编码完成时的回调
        注意：此方法由录音线程调用，需要使用线程安全的方式提交到事件循环
        """
        try:
            if self._loop and not self._loop.is_closed():
                # 使用run_coroutine_threadsafe将协程提交到事件循环
                future = asyncio.run_coroutine_threadsafe(
                    self.ws_client.send_audio(audio_data),
                    self._loop
                )
                # 不等待结果，让它在后台运行
            else:
                logger.error("事件循环不可用，无法发送音频数据")
        except Exception as e:
            logger.error(f"发送音频数据失败: {e}")

    def _on_recording_started(self):
        """当录音开始时的回调"""
        logger.info("🎙️ 录音已开始")
        if self.on_user_speech_start:
            self.on_user_speech_start()

    def _on_recording_stopped(self):
        """当录音停止时的回调"""
        logger.info("⏹️ 录音已停止")

    def _on_recorder_error(self, error: str):
        """当录音出错时的回调"""
        logger.error(f"录音错误: {error}")
        self._trigger_error(f"录音错误: {error}")

    # ========== WebSocket回调 ==========

    def _on_ws_message_received(self, message: Dict[str, Any]):
        """当WebSocket收到消息时的回调"""
        try:
            logger.debug(f"收到WebSocket消息: {message}")

            # 使用解析器解析消息
            parsed_response = self.parser.parse_message(message)

            if parsed_response:
                # 触发AI响应回调
                if self.on_ai_response_received:
                    self.on_ai_response_received(parsed_response)

                # 更新当前消息
                if self.current_message:
                    if parsed_response.text_content:
                        self.current_message.ai_text = parsed_response.text_content
                    if parsed_response.audio_data:
                        # 使用append方法累积音频数据
                        self.current_message.append_audio_chunk(parsed_response.audio_data)
                        logger.info(f"📦 累积音频数据: +{parsed_response.audio_data.size} bytes, 总计: {self.current_message.ai_audio.size if self.current_message.ai_audio else 0} bytes")
                    self.current_message.message_type = parsed_response.message_type

                    # 检查是否收到TTS stop信号(音频播放完成的官方标志)
                    is_tts_stop = (
                        parsed_response.message_type == MessageType.TTS and
                        parsed_response.raw_message and
                        parsed_response.raw_message.get("tts_stop") == True
                    )

                    if is_tts_stop:
                        logger.info(f"🛑 收到TTS stop信号，AI回复完成，保存完整音频到历史记录")
                        if self.config.save_conversation:
                            logger.info(f"💾 保存对话到历史记录 (音频: {self.current_message.ai_audio.size if self.current_message.ai_audio else 0} bytes)")
                            self._save_to_history(self.current_message)
                            # 状态转为READY,允许下一轮对话
                            self._update_state(SessionState.READY)

                    # 如果有音频数据且配置了自动播放，则播放
                    if parsed_response.audio_data and self.config.auto_play_tts:
                        asyncio.create_task(self.player.play_audio(parsed_response.audio_data))

        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}", exc_info=True)

    def _on_ws_disconnected(self, reason: str):
        """当WebSocket断开连接时的回调"""
        logger.warning(f"WebSocket连接已断开: {reason}")
        self._trigger_error(f"连接断开: {reason}")

    def _on_ws_error(self, error: str):
        """当WebSocket出错时的回调"""
        logger.error(f"WebSocket错误: {error}")
        self._trigger_error(f"WebSocket错误: {error}")

    # ========== 解析器回调 ==========

    def _on_text_received(self, text: str):
        """当收到文本消息时的回调"""
        logger.info(f"📝 收到文本: {text}")

        # 注意：不再在这里保存历史记录
        # 历史记录的保存已移到收到Emoji消息时（AI回复完成标志）
        # 这样确保保存的是完整的音频数据，而不是部分数据

        if self.on_user_speech_end:
            self.on_user_speech_end(text)

    def _on_audio_received(self, audio_data: AudioData):
        """
        当收到音频消息时的回调
        注意：TTS音频也会通过这个回调接收
        音频数据会保存到对话历史，由前端播放
        """
        logger.info(f"🔊 收到音频数据: {audio_data.size} bytes, format={audio_data.format}")

        # 后端不播放音频，音频由前端播放
        # 音频数据已经在_on_ws_message_received中保存到current_message.ai_audio
        logger.info("✅ 音频数据已保存到对话历史，等待前端获取")

    def _on_mcp_received(self, mcp_data: Dict[str, Any]):
        """当收到MCP消息时的回调"""
        logger.info(f"📡 收到MCP消息: {mcp_data}")

    def _on_tts_received(self, audio_data: AudioData):
        """当收到TTS消息时的回调"""
        logger.info(f"🔊 收到TTS音频: {audio_data.size} bytes")

        # 只有在配置了auto_play_tts时才播放音频（否则由前端播放）
        if not self.config.auto_play_tts:
            logger.info("⏭️ 后端不播放音频，由前端负责播放")
            return

        # 播放TTS音频
        try:
            # 使用asyncio在事件循环中播放音频
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.player.play_audio(audio_data),
                    self._loop
                )
                logger.info("✅ TTS音频已提交播放")
            else:
                logger.error("事件循环不可用，无法播放TTS音频")
        except Exception as e:
            logger.error(f"播放TTS音频失败: {e}", exc_info=True)

    def _on_parse_error(self, error: str, raw_message: Any):
        """当解析出错时的回调"""
        logger.error(f"消息解析错误: {error}")

    # ========== 播放器回调 ==========

    def _on_playback_started(self, audio_data: AudioData):
        """当播放开始时的回调"""
        logger.info(f"🔊 AI开始说话 ({audio_data.size} bytes)")
        self._update_state(SessionState.SPEAKING)
        if self.on_ai_speaking_start:
            self.on_ai_speaking_start()

    def _on_playback_finished(self):
        """当播放结束时的回调"""
        logger.info("✅ AI说话结束")
        self._update_state(SessionState.READY)
        if self.on_ai_speaking_end:
            self.on_ai_speaking_end()

    def _on_playback_error(self, error: str):
        """当播放出错时的回调"""
        logger.error(f"播放错误: {error}")
        self._trigger_error(f"播放错误: {error}")

    # ========== 对话历史管理 ==========

    def _save_to_history(self, message: VoiceMessage):
        """保存消息到对话历史"""
        self.conversation_history.append(message)
        self.stats["total_messages"] += 1

        # 限制历史记录数量
        if len(self.conversation_history) > self.config.max_conversation_history:
            self.conversation_history.pop(0)

        logger.debug(f"消息已保存到历史记录: {message.message_id}")


# ========== 全局单例实例管理 ==========

_voice_session_manager: Optional[VoiceSessionManager] = None


async def initialize_voice_session(
    device_manager: PocketSpeakDeviceManager,
    session_config: Optional[SessionConfig] = None
) -> bool:
    """
    初始化全局语音会话管理器

    Args:
        device_manager: 设备管理器实例
        session_config: 会话配置

    Returns:
        bool: 初始化是否成功
    """
    global _voice_session_manager

    if _voice_session_manager is not None:
        logger.warning("语音会话管理器已经初始化")
        return True

    _voice_session_manager = VoiceSessionManager(device_manager, session_config)
    return await _voice_session_manager.initialize()


def get_voice_session() -> Optional[VoiceSessionManager]:
    """
    获取全局语音会话管理器实例

    Returns:
        Optional[VoiceSessionManager]: 语音会话管理器实例，如果未初始化则返回None
    """
    return _voice_session_manager


async def close_voice_session():
    """关闭全局语音会话管理器"""
    global _voice_session_manager

    if _voice_session_manager:
        await _voice_session_manager.close()
        _voice_session_manager = None
        logger.info("全局语音会话管理器已关闭")
