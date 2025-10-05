"""
PocketSpeak TTS语音播放模块

基于 py-xiaozhi 的 AudioCodec 实现，提供语音播放功能
负责：OPUS解码 -> 24kHz PCM -> 扬声器播放
同时支持TTS请求发送和音频播放
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json

# 导入py-xiaozhi的音频编解码器
from libs.py_xiaozhi.src.audio_codecs.audio_codec import AudioCodec
from libs.py_xiaozhi.src.constants.constants import AudioConfig

# 导入AI响应解析器的音频数据结构
from services.voice_chat.ai_response_parser import AudioData

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """播放状态枚举"""
    IDLE = "idle"           # 空闲
    PLAYING = "playing"     # 播放中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 停止
    ERROR = "error"         # 错误


@dataclass
class PlaybackConfig:
    """播放配置"""
    output_sample_rate: int = AudioConfig.OUTPUT_SAMPLE_RATE  # 24kHz
    channels: int = AudioConfig.CHANNELS  # 1
    enable_queue: bool = True  # 启用播放队列
    auto_play: bool = True     # 自动播放
    max_queue_size: int = 50   # 最大队列大小


@dataclass
class TTSRequest:
    """TTS请求数据结构"""
    text: str                    # 要合成的文本
    voice_id: Optional[str] = None      # 声音ID
    speed: float = 1.0          # 播放速度
    pitch: float = 1.0          # 音调
    volume: float = 1.0         # 音量
    language: str = "zh-CN"     # 语言


class TTSPlayer:
    """
    TTS语音播放器

    功能：
    1. 发送TTS合成请求
    2. 接收并解码OPUS音频数据
    3. 播放音频到扬声器
    4. 管理播放队列
    5. 控制播放状态
    """

    def __init__(self, config: Optional[PlaybackConfig] = None):
        """
        初始化TTS播放器

        Args:
            config: 播放配置，如果为None则使用默认配置
        """
        self.config = config or PlaybackConfig()
        self.audio_codec: Optional[AudioCodec] = None
        self.is_initialized = False

        # 播放状态
        self.state = PlaybackState.IDLE
        self.current_audio: Optional[AudioData] = None

        # 播放队列
        self.audio_queue: List[AudioData] = []
        self.queue_lock = asyncio.Lock()

        # 回调函数
        self.on_playback_started: Optional[Callable[[AudioData], None]] = None
        self.on_playback_finished: Optional[Callable[[], None]] = None
        self.on_playback_error: Optional[Callable[[str], None]] = None
        self.on_tts_request_sent: Optional[Callable[[TTSRequest], None]] = None

        # TTS请求发送回调（用于发送WebSocket消息）
        self.send_tts_request: Optional[Callable[[Dict], None]] = None

        # 播放统计
        self.stats = {
            "total_played": 0,
            "total_duration": 0.0,
            "queue_overflow": 0,
            "playback_errors": 0
        }

        logger.info("TTS播放器初始化完成")

    async def initialize(self) -> bool:
        """
        初始化音频设备

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("正在初始化音频播放设备...")

            # 创建音频编解码器实例
            self.audio_codec = AudioCodec()

            # 初始化音频设备
            await self.audio_codec.initialize()

            self.is_initialized = True
            logger.info("音频播放设备初始化成功")
            return True

        except Exception as e:
            error_msg = f"音频播放设备初始化失败: {e}"
            logger.error(error_msg)
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

    async def request_tts(self, request: TTSRequest) -> bool:
        """
        发送TTS合成请求

        Args:
            request: TTS请求

        Returns:
            bool: 请求是否发送成功
        """
        if not self.send_tts_request:
            error_msg = "TTS请求发送回调未设置"
            logger.error(error_msg)
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

        try:
            # 构造TTS请求消息
            tts_message = {
                "type": "tts",
                "action": "synthesize",
                "data": {
                    "text": request.text,
                    "voice_id": request.voice_id,
                    "speed": request.speed,
                    "pitch": request.pitch,
                    "volume": request.volume,
                    "language": request.language,
                    "format": "opus",
                    "sample_rate": self.config.output_sample_rate
                }
            }

            # 发送TTS请求
            self.send_tts_request(tts_message)

            logger.info(f"发送TTS请求: {request.text[:50]}...")

            if self.on_tts_request_sent:
                self.on_tts_request_sent(request)

            return True

        except Exception as e:
            error_msg = f"发送TTS请求失败: {e}"
            logger.error(error_msg)
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

    async def play_audio(self, audio_data: AudioData) -> bool:
        """
        播放音频数据

        Args:
            audio_data: 要播放的音频数据

        Returns:
            bool: 播放是否成功启动
        """
        import traceback
        logger.warning(f"⚠️ play_audio被调用！音频大小: {len(audio_data.data)} bytes")
        logger.warning(f"⚠️ 后端不应该播放音频！直接返回False")
        return False  # 后端禁止播放音频，音频应该由前端播放

        if not self.is_initialized:
            error_msg = "播放器未初始化，请先调用initialize()"
            logger.error(error_msg)
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

        try:
            if self.config.enable_queue and self.state == PlaybackState.PLAYING:
                # 如果正在播放且启用队列，则加入队列
                await self._add_to_queue(audio_data)
                return True
            else:
                # 直接播放
                return await self._play_audio_direct(audio_data)

        except Exception as e:
            error_msg = f"播放音频失败: {e}"
            logger.error(error_msg)
            self.stats["playback_errors"] += 1
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

    async def _add_to_queue(self, audio_data: AudioData):
        """
        添加音频到播放队列

        Args:
            audio_data: 音频数据
        """
        async with self.queue_lock:
            if len(self.audio_queue) >= self.config.max_queue_size:
                # 队列满时移除最旧的音频
                removed = self.audio_queue.pop(0)
                self.stats["queue_overflow"] += 1
                logger.warning(f"播放队列已满，移除旧音频 ({len(removed.data)} 字节)")

            self.audio_queue.append(audio_data)
            logger.info(f"音频加入播放队列，当前队列长度: {len(self.audio_queue)}")

    async def _play_audio_direct(self, audio_data: AudioData) -> bool:
        """
        直接播放音频

        Args:
            audio_data: 音频数据

        Returns:
            bool: 播放是否成功启动
        """
        try:
            self.state = PlaybackState.PLAYING
            self.current_audio = audio_data

            # 启动音频流
            await self.audio_codec.start_streams()

            # 写入音频数据进行播放
            await self.audio_codec.write_audio(audio_data.data)

            logger.info(f"开始播放音频: {len(audio_data.data)} 字节")

            if self.on_playback_started:
                self.on_playback_started(audio_data)

            # 等待播放完成
            await self._wait_for_playback_complete()

            return True

        except Exception as e:
            self.state = PlaybackState.ERROR
            logger.error(f"播放音频失败: {e}")
            raise

    async def _wait_for_playback_complete(self):
        """等待音频播放完成"""
        try:
            # 等待音频播放完成
            await self.audio_codec.wait_for_audio_complete()

            self.state = PlaybackState.IDLE
            self.stats["total_played"] += 1

            logger.info("音频播放完成")

            if self.on_playback_finished:
                self.on_playback_finished()

            # 检查是否有队列中的音频需要播放
            await self._play_next_in_queue()

        except Exception as e:
            self.state = PlaybackState.ERROR
            logger.error(f"等待播放完成时出错: {e}")

    async def _play_next_in_queue(self):
        """播放队列中的下一个音频"""
        if not self.config.enable_queue or not self.config.auto_play:
            return

        async with self.queue_lock:
            if self.audio_queue and self.state == PlaybackState.IDLE:
                next_audio = self.audio_queue.pop(0)
                logger.info(f"播放队列中的下一个音频，剩余队列长度: {len(self.audio_queue)}")

                # 异步播放下一个音频（不阻塞）
                asyncio.create_task(self._play_audio_direct(next_audio))

    async def stop_playback(self) -> bool:
        """
        停止当前播放

        Returns:
            bool: 停止是否成功
        """
        try:
            if self.state == PlaybackState.PLAYING:
                await self.audio_codec.clear_audio_queue()
                self.state = PlaybackState.STOPPED
                logger.info("停止音频播放")

            return True

        except Exception as e:
            error_msg = f"停止播放失败: {e}"
            logger.error(error_msg)
            if self.on_playback_error:
                self.on_playback_error(error_msg)
            return False

    async def clear_queue(self):
        """清空播放队列"""
        async with self.queue_lock:
            cleared_count = len(self.audio_queue)
            self.audio_queue.clear()
            logger.info(f"清空播放队列，移除 {cleared_count} 个音频")

    def set_tts_request_sender(self, sender: Callable[[Dict], None]):
        """
        设置TTS请求发送函数

        Args:
            sender: 发送函数，用于发送WebSocket消息
        """
        self.send_tts_request = sender
        logger.info("设置TTS请求发送函数")

    def set_callbacks(self,
                     on_started: Optional[Callable[[AudioData], None]] = None,
                     on_finished: Optional[Callable[[], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None,
                     on_tts_sent: Optional[Callable[[TTSRequest], None]] = None):
        """
        设置回调函数

        Args:
            on_started: 播放开始回调
            on_finished: 播放完成回调
            on_error: 错误回调
            on_tts_sent: TTS请求发送回调
        """
        self.on_playback_started = on_started
        self.on_playback_finished = on_finished
        self.on_playback_error = on_error
        self.on_tts_request_sent = on_tts_sent
        logger.info("设置播放器回调函数")

    def get_playback_status(self) -> Dict[str, Any]:
        """
        获取播放器状态

        Returns:
            Dict: 状态信息
        """
        status = {
            "is_initialized": self.is_initialized,
            "state": self.state.value,
            "queue_length": len(self.audio_queue),
            "current_audio": {
                "format": self.current_audio.format if self.current_audio else None,
                "size": len(self.current_audio.data) if self.current_audio else 0
            } if self.current_audio else None,
            "config": {
                "output_sample_rate": self.config.output_sample_rate,
                "channels": self.config.channels,
                "enable_queue": self.config.enable_queue,
                "auto_play": self.config.auto_play,
                "max_queue_size": self.config.max_queue_size
            },
            "stats": self.stats.copy()
        }

        if self.audio_codec:
            try:
                status["audio_device"] = {
                    "output_sample_rate": getattr(self.audio_codec, 'device_output_sample_rate', None),
                    "speaker_device_id": getattr(self.audio_codec, 'speaker_device_id', None)
                }
            except Exception as e:
                logger.warning(f"获取音频设备状态失败: {e}")

        return status

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取播放队列状态

        Returns:
            Dict: 队列状态信息
        """
        return {
            "queue_length": len(self.audio_queue),
            "queue_items": [
                {
                    "format": audio.format,
                    "size": len(audio.data),
                    "sample_rate": audio.sample_rate,
                    "channels": audio.channels
                }
                for audio in self.audio_queue
            ],
            "max_queue_size": self.config.max_queue_size,
            "queue_overflow_count": self.stats["queue_overflow"]
        }

    def is_playing(self) -> bool:
        """
        检查是否正在播放

        Returns:
            bool: 是否正在播放
        """
        return self.state == PlaybackState.PLAYING

    def is_idle(self) -> bool:
        """
        检查是否空闲

        Returns:
            bool: 是否空闲
        """
        return self.state == PlaybackState.IDLE

    async def close(self):
        """
        关闭播放器并释放资源
        """
        try:
            await self.stop_playback()
            await self.clear_queue()

            if self.audio_codec:
                await self.audio_codec.close()
                self.audio_codec = None

            self.is_initialized = False
            self.state = PlaybackState.IDLE
            logger.info("TTS播放器已关闭")

        except Exception as e:
            logger.error(f"关闭TTS播放器失败: {e}")

    def __del__(self):
        """析构函数"""
        if self.is_initialized:
            logger.warning("TTSPlayer未正确关闭，请调用close()")


# 便捷函数
async def create_tts_player(config: Optional[PlaybackConfig] = None) -> Optional[TTSPlayer]:
    """
    创建并初始化TTS播放器

    Args:
        config: 播放配置

    Returns:
        TTSPlayer: 初始化成功的播放器，失败时返回None
    """
    player = TTSPlayer(config)

    if await player.initialize():
        return player
    else:
        await player.close()
        return None


# 示例使用
if __name__ == "__main__":
    async def test_tts_player():
        """测试TTS播放器"""

        def on_playback_started(audio: AudioData):
            print(f"播放开始: {len(audio.data)} 字节")

        def on_playback_finished():
            print("播放完成")

        def on_playback_error(error: str):
            print(f"播放错误: {error}")

        def on_tts_sent(request: TTSRequest):
            print(f"TTS请求已发送: {request.text}")

        def mock_tts_sender(message: Dict):
            print(f"模拟发送TTS请求: {message}")

        # 创建播放器
        player = await create_tts_player()
        if not player:
            print("创建播放器失败")
            return

        # 设置回调
        player.set_callbacks(
            on_started=on_playback_started,
            on_finished=on_playback_finished,
            on_error=on_playback_error,
            on_tts_sent=on_tts_sent
        )

        # 设置TTS请求发送函数
        player.set_tts_request_sender(mock_tts_sender)

        # 测试TTS请求
        tts_request = TTSRequest(
            text="你好，这是一个测试",
            language="zh-CN"
        )

        if await player.request_tts(tts_request):
            print("TTS请求发送成功")

        # 模拟播放一些音频数据
        # 注意：这里需要真实的OPUS音频数据才能实际播放
        # test_audio = AudioData(data=b"fake_opus_data", format="opus")
        # await player.play_audio(test_audio)

        # 获取状态
        status = player.get_playback_status()
        print(f"播放器状态: {status}")

        # 关闭播放器
        await player.close()

    # 运行测试
    asyncio.run(test_tts_player())