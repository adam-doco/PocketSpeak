"""
PocketSpeak 语音会话管理器

整合WebSocket连接、语音录制、AI响应解析和TTS播放模块
提供完整的语音交互会话管理功能
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, List, Set
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

# ✅ 新增：导入音频缓冲管理器
from services.voice_chat.audio_buffer_manager import create_sentence_buffer, AudioChunk

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
    _is_tts_complete: bool = field(default=False, init=False)  # TTS是否完成（收到tts_stop信号）
    _sentences: List[Dict[str, Any]] = field(default_factory=list, init=False)  # 句子列表: [{"text": "...", "start_chunk": 0, "end_chunk": 5, "is_complete": True}, ...]
    _current_sentence_start: int = field(default=0, init=False)  # 当前句子的起始chunk索引

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

    def get_incremental_audio(self, last_chunk_index: int) -> Dict[str, Any]:
        """
        获取增量音频数据（用于流式播放）

        Args:
            last_chunk_index: 前端已获取到的PCM块索引

        Returns:
            Dict包含:
            - has_new_audio: 是否有新音频
            - audio_data: Base64编码的新增PCM数据（如果有）
            - chunk_count: 当前总块数
            - is_complete: TTS是否完成
            - sample_rate: 采样率
            - channels: 声道数
        """
        import base64

        # 检查是否有新的音频块
        if last_chunk_index < len(self._pcm_chunks):
            # 获取新增的PCM块
            new_chunks = self._pcm_chunks[last_chunk_index:]
            merged_new_pcm = b''.join(new_chunks)

            # 合并从开始到现在的所有PCM（用于覆盖式播放）
            merged_all_pcm = b''.join(self._pcm_chunks)

            return {
                "has_new_audio": True,
                "audio_data": base64.b64encode(merged_all_pcm).decode('utf-8'),  # 返回完整累积音频
                "new_audio_size": len(merged_new_pcm),
                "total_audio_size": len(merged_all_pcm),
                "chunk_count": len(self._pcm_chunks),
                "is_complete": self._is_tts_complete,
                "sample_rate": self._sample_rate,
                "channels": self._channels
            }

        # 没有新音频
        return {
            "has_new_audio": False,
            "chunk_count": len(self._pcm_chunks),
            "is_complete": self._is_tts_complete
        }

    def add_text_sentence(self, text: str):
        """
        添加新的文本句子
        调用时机: 收到AI文本消息时
        作用:
        1. 标记上一句的音频已完成,开始新句子
        2. 追加文本到ai_text字段(用于聊天界面显示完整内容)
        """
        import logging
        logger = logging.getLogger(__name__)

        # 如果有上一句,标记其完成
        if len(self._sentences) > 0 and not self._sentences[-1]["is_complete"]:
            self._sentences[-1]["end_chunk"] = len(self._pcm_chunks)
            self._sentences[-1]["is_complete"] = True
            logger.info(f"✅ 句子音频完成: '{self._sentences[-1]['text']}', chunks [{self._sentences[-1]['start_chunk']}, {self._sentences[-1]['end_chunk']})")

        # 添加新句子
        new_sentence = {
            "text": text,
            "start_chunk": len(self._pcm_chunks),
            "end_chunk": None,
            "is_complete": False
        }
        self._sentences.append(new_sentence)
        self._current_sentence_start = len(self._pcm_chunks)
        logger.info(f"📝 新句子开始: '{text}', start_chunk={self._current_sentence_start}")

        # ✅ 追加文本到ai_text字段(用于聊天界面显示)
        if self.ai_text:
            self.ai_text += text
        else:
            self.ai_text = text

    def mark_tts_complete(self):
        """标记TTS完成"""
        import logging
        logger = logging.getLogger(__name__)

        self._is_tts_complete = True

        # 标记最后一句完成
        if len(self._sentences) > 0 and not self._sentences[-1]["is_complete"]:
            self._sentences[-1]["end_chunk"] = len(self._pcm_chunks)
            self._sentences[-1]["is_complete"] = True
            logger.info(f"✅ 最后一句音频完成: '{self._sentences[-1]['text']}', chunks [{self._sentences[-1]['start_chunk']}, {self._sentences[-1]['end_chunk']})")

    def get_completed_sentences(self, last_sentence_index: int) -> Dict[str, Any]:
        """
        获取已完成的句子及其音频

        Args:
            last_sentence_index: 前端已获取到的句子索引

        Returns:
            {
                "has_new_sentences": bool,
                "sentences": [
                    {
                        "text": "句子文本",
                        "audio_data": "base64编码的WAV音频"
                    },
                    ...
                ],
                "total_sentences": 总句子数,
                "is_complete": TTS是否完成
            }
        """
        import base64
        import io
        import wave

        # 获取新完成的句子
        completed_sentences = [s for s in self._sentences if s["is_complete"]]

        if last_sentence_index < len(completed_sentences):
            new_sentences = completed_sentences[last_sentence_index:]

            result_sentences = []
            for sentence in new_sentences:
                # 提取这句话的音频chunks
                start = sentence["start_chunk"]
                end = sentence["end_chunk"]

                # ✅ 跳过空音频句子(start == end表示没有音频数据)
                if start == end:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"⚠️ 句子'{sentence['text']}'音频为空(chunks [{start}, {end})),跳过")
                    continue

                sentence_pcm_chunks = self._pcm_chunks[start:end]
                sentence_pcm = b''.join(sentence_pcm_chunks)

                # 转换为WAV格式
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(self._channels)
                    wav_file.setsampwidth(2)  # 16-bit PCM
                    wav_file.setframerate(self._sample_rate)
                    wav_file.writeframes(sentence_pcm)

                wav_data = wav_buffer.getvalue()
                wav_base64 = base64.b64encode(wav_data).decode('utf-8')

                result_sentences.append({
                    "text": sentence["text"],
                    "audio_data": wav_base64
                })

            # ✅ 只有真正有音频的句子才返回
            if result_sentences:
                return {
                    "has_new_sentences": True,
                    "sentences": result_sentences,
                    "total_sentences": len(completed_sentences),
                    "is_complete": self._is_tts_complete
                }
            else:
                # 所有新句子都被过滤了,返回无新句子
                return {
                    "has_new_sentences": False,
                    "total_sentences": len(completed_sentences),
                    "is_complete": self._is_tts_complete
                }

        return {
            "has_new_sentences": False,
            "total_sentences": len(completed_sentences),
            "is_complete": self._is_tts_complete
        }


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

        # 后台任务管理（参考py-xiaozhi标准实现）
        self._bg_tasks: Set[asyncio.Task] = set()
        self._send_audio_semaphore: Optional[asyncio.Semaphore] = None  # 在initialize中创建

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
        # 🚀 新增：音频帧实时推送回调（模仿py-xiaozhi的即时播放）
        self.on_text_received: Optional[Callable[[str], None]] = None  # 文本推送回调
        self.on_audio_frame_received: Optional[Callable[[bytes], None]] = None
        self.on_emoji_received: Optional[Callable[[str, str], None]] = None  # 🎭 新增：emoji推送回调(emoji, emotion)

        # 统计信息
        self.stats = {
            "total_messages": 0,
            "total_user_speech_time": 0.0,
            "total_ai_response_time": 0.0,
            "session_start_time": None,
            "session_uptime": 0.0
        }

        # ✅ 新增：初始化音频缓冲队列（渐进式优化）
        try:
            self.sentence_buffer = create_sentence_buffer(preload_count=2)
            logger.info("✅ 音频缓冲队列已初始化 (maxsize=500, threshold=0.5s)")
        except Exception as e:
            logger.warning(f"⚠️ 音频缓冲队列初始化失败（不影响功能）: {e}")
            self.sentence_buffer = None

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

            # 0.1 初始化音频发送并发控制（参考py-xiaozhi标准实现）
            self._send_audio_semaphore = asyncio.Semaphore(10)  # 最多10个并发发送任务
            logger.info("✅ 音频发送并发控制已初始化 (max_concurrent=10)")

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
        self.parser.on_emoji_received = self._on_emoji_received  # 🎭 新增：emoji回调
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

            # 步骤1：先开始本地录音（启动音频流）
            # 优化：先启动录音再通知服务器，减少服务器等待时间
            # 参考：py-xiaozhi 在发送 start_listening 前已经启动了音频流
            if not await self.recorder.start_recording():
                error_msg = "无法开始录音"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 步骤2：清空音频缓冲（参考py-xiaozhi标准实现）
            # 确保发送的是新鲜的音频数据，不包含旧缓冲
            await self.recorder.clear_audio_buffers()

            # 步骤3：发送开始监听消息到服务器（遵循py-xiaozhi协议）
            # 使用MANUAL模式（手动按压，匹配前端的按住说话交互）
            # 重要：前端使用按住说话/松开停止的交互模式，必须使用 manual 模式
            # auto 模式会等待 VAD 检测静音，导致延迟
            mode = "manual"  # 可选: "auto"(VAD自动), "manual"(手动按压), "realtime"(实时打断)
            success = await self.ws_client.send_start_listening(mode)
            if not success:
                # 发送失败，回滚：停止录音
                await self.recorder.stop_recording()
                error_msg = "发送开始监听消息失败"
                logger.error(error_msg)
                self._trigger_error(error_msg)
                return False

            # 步骤4：更新状态
            self._update_state(SessionState.LISTENING)

            # 步骤5：创建新的消息对象
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
            import time
            t0 = time.time()
            logger.info("⏹️ 停止监听用户语音...")

            # 步骤1：停止本地录音
            await self.recorder.stop_recording()
            t1 = time.time()
            logger.info(f"⏱️ 停止录音耗时: {(t1-t0)*1000:.0f}ms")

            # 步骤2：发送停止监听消息到服务器（遵循py-xiaozhi协议）
            success = await self.ws_client.send_stop_listening()
            t2 = time.time()
            logger.info(f"⏱️ 发送stop_listening耗时: {(t2-t1)*1000:.0f}ms")

            if not success:
                logger.warning("发送停止监听消息失败，但本地录音已停止")

            # 步骤3：更新状态为处理中
            self._update_state(SessionState.PROCESSING)

            # 🔥 记录时间戳，用于计算延迟
            self._stop_listening_time = time.time()
            self._first_audio_received = False  # 重置标志

            logger.info(f"✅ 停止监听完成，等待AI响应... (总耗时: {(t2-t0)*1000:.0f}ms)")

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
            # 取消所有后台任务（参考py-xiaozhi标准实现）
            if self._bg_tasks:
                logger.info(f"取消 {len(self._bg_tasks)} 个后台任务...")
                for task in self._bg_tasks:
                    task.cancel()

                # 等待任务结束
                await asyncio.gather(*self._bg_tasks, return_exceptions=True)
                self._bg_tasks.clear()
                logger.info("✅ 后台任务已清理")

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
            await self.recorder.close()  # 修复：SpeechRecorder 使用 close() 不是 cleanup()
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
        当音频编码完成时的回调（优化版 - 参考py-xiaozhi标准实现）

        注意：此方法由音频硬件驱动线程调用，需要使用线程安全的方式提交到事件循环

        优化说明：
        1. 使用 call_soon_threadsafe 替代 run_coroutine_threadsafe（减少调度开销）
        2. 添加并发控制信号量（避免任务风暴）
        3. 统一管理后台任务（避免内存泄漏）

        参考：libs/py_xiaozhi/src/application.py:388-412
        """
        try:
            if self._loop and not self._loop.is_closed():
                # 🟢 使用 call_soon_threadsafe 跨线程调度（参考py-xiaozhi）
                self._loop.call_soon_threadsafe(
                    self._schedule_audio_send_task, audio_data
                )
            else:
                logger.error("事件循环不可用，无法发送音频数据")
        except Exception as e:
            logger.error(f"调度音频发送任务失败: {e}")

    def _schedule_audio_send_task(self, audio_data: bytes):
        """
        在主事件循环中创建音频发送任务（参考py-xiaozhi标准实现）

        此方法由 _on_audio_encoded 通过 call_soon_threadsafe 调度，
        确保在主事件循环中执行，可以安全地创建异步任务。

        参考：libs/py_xiaozhi/src/application.py:397-412
        """
        try:
            # 并发限制，避免任务风暴
            async def _send():
                async with self._send_audio_semaphore:
                    await self.ws_client.send_audio(audio_data)

            # 创建后台任务
            task = asyncio.create_task(_send())
            self._bg_tasks.add(task)

            # 任务完成后从集合中移除
            def done_callback(t):
                self._bg_tasks.discard(t)
                if not t.cancelled() and t.exception():
                    logger.error(f"音频发送任务异常: {t.exception()}", exc_info=True)

            task.add_done_callback(done_callback)

        except Exception as e:
            logger.error(f"创建音频发送任务失败: {e}", exc_info=True)

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
                # ⭐ 特殊处理：STT消息（用户语音识别结果）
                if parsed_response.message_type == MessageType.STT:
                    if self.current_message and parsed_response.text_content:
                        # 立即保存用户文字
                        self.current_message.user_text = parsed_response.text_content
                        logger.info(f"✅ 用户语音识别结果: {parsed_response.text_content}")

                        # 触发用户说话结束回调
                        if self.on_user_speech_end:
                            self.on_user_speech_end(parsed_response.text_content)

                        # ⭐ 关键：立即保存用户消息到历史记录，前端轮询就能立即获取
                        if self.config.save_conversation:
                            logger.info(f"💾 立即保存用户消息到历史记录")
                            self._save_to_history(self.current_message)

                    return  # STT消息处理完毕，不继续后续逻辑

                # ❌ 删除: 不再通过on_ai_response_received推送文本，避免重复
                # 文本通过_on_text_received → on_text_received推送
                # 音频通过on_audio_frame_received直接推送

                # 更新当前消息
                if self.current_message:
                    # ⚠️ 注意：文本和音频都通过解析器回调处理
                    # - 文本：_on_text_received → self.on_text_received(text)
                    # - 音频：_on_audio_received → self.on_audio_frame_received(pcm_data)

                    if parsed_response.audio_data:
                        # 使用append方法累积音频数据（用于历史记录保存）
                        self.current_message.append_audio_chunk(parsed_response.audio_data)

                        # 🔥 关键：记录第一帧音频到达时间
                        if not hasattr(self, '_first_audio_received'):
                            self._first_audio_received = True
                            if hasattr(self, '_stop_listening_time'):
                                import time
                                delay = (time.time() - self._stop_listening_time) * 1000
                                logger.info(f"⏱️ 【首帧延迟】{delay:.0f}ms")

                        # ✅ 新增：同步到缓冲队列（异步，不阻塞）
                        if self.sentence_buffer:
                            asyncio.create_task(self._add_to_buffer_safe(parsed_response))
                    self.current_message.message_type = parsed_response.message_type

                    # 检查是否收到TTS stop信号(音频播放完成的官方标志)
                    is_tts_stop = (
                        parsed_response.message_type == MessageType.TTS and
                        parsed_response.raw_message and
                        parsed_response.raw_message.get("tts_stop") == True
                    )

                    if is_tts_stop:
                        logger.info(f"🛑 收到TTS stop信号，AI回复完成，保存完整音频到历史记录")
                        # 标记TTS完成（用于增量音频API）
                        self.current_message.mark_tts_complete()
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

        # 🔥 关键逻辑：判断这是用户的语音识别结果还是AI的回复
        if self.current_message:
            # 如果current_message还没有user_text,说明这是用户的语音识别结果
            if self.current_message.user_text is None:
                self.current_message.user_text = text
                logger.info(f"✅ 用户语音识别结果: {text}")

                # 触发用户说话结束回调
                if self.on_user_speech_end:
                    self.on_user_speech_end(text)
            else:
                # 已经有user_text,说明这是AI的回复文本

                # 🚀 去重检查：避免重复处理相同的文本
                if hasattr(self, '_last_ai_text') and self._last_ai_text == text:
                    logger.debug(f"⚠️ DEBUG: 重复文本，跳过: {text}")
                    return

                self._last_ai_text = text
                self.current_message.add_text_sentence(text)
                logger.info(f"🤖 AI回复句子: {text}")

                # 🚀 立即推送AI文本给前端 (模仿py-xiaozhi)
                if self.on_text_received:
                    self.on_text_received(text)

        # 注意：不再在这里保存历史记录
        # 历史记录的保存已移到收到TTS stop信号时（AI回复完成标志）
        # 这样确保保存的是完整的音频数据，而不是部分数据

    def _on_audio_received(self, audio_data: AudioData):
        """
        当收到音频消息时的回调（解析器触发）
        🚀 在这里立即解码并推送音频帧给前端（模仿py-xiaozhi）
        """
        # 🚀 立即推送音频帧给前端（模仿py-xiaozhi的即时播放）
        if self.on_audio_frame_received:
            try:
                # 解码OPUS为PCM（模仿py-xiaozhi的write_audio逻辑）
                import opuslib
                if not hasattr(self, '_streaming_opus_decoder'):
                    # 初始化流式解码器（24kHz, 单声道）
                    self._streaming_opus_decoder = opuslib.Decoder(24000, 1)
                    logger.info("✅ 流式OPUS解码器已初始化")
                    # 初始化帧计数器
                    self._audio_frame_count = 0

                # 解码OPUS为PCM（960帧 = 24000Hz * 0.04s）
                pcm_data = self._streaming_opus_decoder.decode(
                    audio_data.data,
                    frame_size=960,
                    decode_fec=False
                )

                # 调用回调推送给前端
                self.on_audio_frame_received(pcm_data)

                # 每10帧输出一次日志（避免日志过多）
                self._audio_frame_count += 1
                if self._audio_frame_count % 10 == 0:
                    logger.info(f"🎵 已推送 {self._audio_frame_count} 帧音频")
            except Exception as e:
                logger.error(f"❌ 音频帧推送回调失败: {e}", exc_info=True)
        else:
            logger.warning("⚠️ on_audio_frame_received 回调未设置，音频帧未推送")

    def _on_emoji_received(self, emoji: str, emotion: str):
        """
        当收到Emoji消息时的回调（AI回复结束标志）
        🎭 立即推送给前端用于播放Live2D表情
        """
        logger.info(f"🎭 收到Emoji: {emoji} ({emotion})")

        # 🚀 立即推送emoji给前端（模仿py-xiaozhi）
        if self.on_emoji_received:
            self.on_emoji_received(emoji, emotion)
            logger.debug(f"🎭 Emoji已推送给前端: {emoji}")

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

    # ========== 音频缓冲队列同步 ==========

    async def _add_to_buffer_safe(self, parsed_response):
        """
        安全地将音频数据添加到缓冲队列

        注意：此方法失败不影响主流程
        """
        try:
            chunk = AudioChunk(
                chunk_id=f"chunk_{int(datetime.now().timestamp() * 1000)}",
                audio_data=parsed_response.audio_data.data,
                text=parsed_response.text_content or "",
                format=parsed_response.audio_data.format,
                sample_rate=parsed_response.audio_data.sample_rate,
                channels=parsed_response.audio_data.channels
            )

            await self.sentence_buffer.audio_buffer.put(chunk)
            logger.debug(f"✅ 音频已加入缓冲队列: {len(chunk.audio_data)} bytes")

        except Exception as e:
            # 失败仅记录日志，不抛出异常
            logger.debug(f"添加到缓冲队列失败（不影响功能）: {e}")


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
