"""
PocketSpeak 语音录制和发送模块

基于 py-xiaozhi 的 AudioCodec 实现，提供语音录制、OPUS编码和实时发送功能
负责：麦克风采集 -> 重采样16kHz -> OPUS编码 -> WebSocket发送
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import numpy as np

# 导入py-xiaozhi的音频编解码器
from libs.py_xiaozhi.src.audio_codecs.audio_codec import AudioCodec
from libs.py_xiaozhi.src.constants.constants import AudioConfig

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """录音配置"""
    sample_rate: int = AudioConfig.INPUT_SAMPLE_RATE  # 16kHz
    channels: int = AudioConfig.CHANNELS  # 1
    frame_duration: int = AudioConfig.FRAME_DURATION  # 40ms
    enable_aec: bool = True  # 声学回声消除


class SpeechRecorder:
    """
    语音录制器

    功能：
    1. 初始化音频设备和编码器
    2. 开始/停止录音
    3. 实时OPUS编码
    4. 通过回调发送编码数据
    """

    def __init__(self, config: Optional[RecordingConfig] = None):
        """
        初始化语音录制器

        Args:
            config: 录音配置，如果为None则使用默认配置
        """
        self.config = config or RecordingConfig()
        self.audio_codec: Optional[AudioCodec] = None
        self.is_recording = False
        self.is_initialized = False

        # 编码音频数据回调函数
        self.on_audio_encoded: Optional[Callable[[bytes], None]] = None

        # 状态回调函数
        self.on_recording_started: Optional[Callable[[], None]] = None
        self.on_recording_stopped: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        logger.info("语音录制器初始化完成")

    async def initialize(self) -> bool:
        """
        初始化音频设备和编码器

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("正在初始化音频设备...")

            # 创建音频编解码器实例
            self.audio_codec = AudioCodec()

            # 初始化音频设备
            await self.audio_codec.initialize()

            # 设置编码回调
            self.audio_codec.set_encoded_audio_callback(self._on_encoded_audio)

            # 配置AEC
            if hasattr(self.audio_codec, 'toggle_aec'):
                self.audio_codec.toggle_aec(self.config.enable_aec)
                logger.info(f"AEC状态: {'启用' if self.config.enable_aec else '禁用'}")

            self.is_initialized = True
            logger.info("音频设备初始化成功")
            return True

        except Exception as e:
            error_msg = f"音频设备初始化失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

    def _on_encoded_audio(self, encoded_data: bytes):
        """
        编码音频数据回调（由AudioCodec调用）

        Args:
            encoded_data: OPUS编码的音频数据
        """
        try:
            if self.is_recording and self.on_audio_encoded:
                self.on_audio_encoded(encoded_data)
        except Exception as e:
            logger.error(f"处理编码音频数据失败: {e}")

    async def start_recording(self) -> bool:
        """
        开始录音

        Returns:
            bool: 启动是否成功
        """
        if not self.is_initialized:
            error_msg = "录制器未初始化，请先调用initialize()"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

        if self.is_recording:
            logger.warning("录音已在进行中")
            return True

        try:
            # 启动音频流
            await self.audio_codec.start_streams()

            self.is_recording = True
            logger.info("开始录音")

            if self.on_recording_started:
                self.on_recording_started()

            return True

        except Exception as e:
            error_msg = f"启动录音失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

    async def stop_recording(self) -> bool:
        """
        停止录音

        Returns:
            bool: 停止是否成功
        """
        if not self.is_recording:
            logger.warning("录音未在进行中")
            return True

        try:
            self.is_recording = False

            # 停止音频流
            await self.audio_codec.stop_streams()

            logger.info("停止录音")

            if self.on_recording_stopped:
                self.on_recording_stopped()

            return True

        except Exception as e:
            error_msg = f"停止录音失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """
        设置编码音频数据回调函数

        Args:
            callback: 回调函数，接收OPUS编码的音频数据
        """
        self.on_audio_encoded = callback
        logger.info("设置音频编码回调")

    def set_status_callbacks(self,
                           on_started: Optional[Callable[[], None]] = None,
                           on_stopped: Optional[Callable[[], None]] = None,
                           on_error: Optional[Callable[[str], None]] = None):
        """
        设置状态回调函数

        Args:
            on_started: 录音开始回调
            on_stopped: 录音停止回调
            on_error: 错误回调
        """
        self.on_recording_started = on_started
        self.on_recording_stopped = on_stopped
        self.on_error = on_error
        logger.info("设置状态回调")

    def get_recording_status(self) -> Dict[str, Any]:
        """
        获取录音状态信息

        Returns:
            Dict: 状态信息
        """
        status = {
            "is_initialized": self.is_initialized,
            "is_recording": self.is_recording,
            "config": {
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "frame_duration": self.config.frame_duration,
                "enable_aec": self.config.enable_aec
            }
        }

        if self.audio_codec:
            # 获取音频设备状态
            try:
                status["audio_device"] = {
                    "input_sample_rate": getattr(self.audio_codec, 'device_input_sample_rate', None),
                    "mic_device_id": getattr(self.audio_codec, 'mic_device_id', None),
                    "aec_enabled": self.audio_codec.is_aec_enabled() if hasattr(self.audio_codec, 'is_aec_enabled') else False
                }

                if hasattr(self.audio_codec, 'get_aec_status'):
                    status["aec_status"] = self.audio_codec.get_aec_status()

            except Exception as e:
                logger.warning(f"获取音频设备状态失败: {e}")

        return status

    def toggle_aec(self, enabled: bool) -> bool:
        """
        切换声学回声消除

        Args:
            enabled: 是否启用AEC

        Returns:
            bool: 实际的AEC状态
        """
        self.config.enable_aec = enabled

        if self.audio_codec and hasattr(self.audio_codec, 'toggle_aec'):
            return self.audio_codec.toggle_aec(enabled)

        logger.warning("AudioCodec不支持AEC切换")
        return False

    async def clear_audio_buffers(self):
        """清空音频缓冲区"""
        if self.audio_codec:
            await self.audio_codec.clear_audio_queue()
            logger.info("清空音频缓冲区")

    async def close(self):
        """
        关闭录制器并释放资源
        """
        try:
            if self.is_recording:
                await self.stop_recording()

            if self.audio_codec:
                await self.audio_codec.close()
                self.audio_codec = None

            self.is_initialized = False
            logger.info("语音录制器已关闭")

        except Exception as e:
            logger.error(f"关闭语音录制器失败: {e}")

    def __del__(self):
        """析构函数"""
        if self.is_initialized:
            logger.warning("SpeechRecorder未正确关闭，请调用close()")


# 便捷函数
async def create_speech_recorder(config: Optional[RecordingConfig] = None) -> Optional[SpeechRecorder]:
    """
    创建并初始化语音录制器

    Args:
        config: 录音配置

    Returns:
        SpeechRecorder: 初始化成功的录制器，失败时返回None
    """
    recorder = SpeechRecorder(config)

    if await recorder.initialize():
        return recorder
    else:
        await recorder.close()
        return None


# 示例使用
if __name__ == "__main__":
    async def test_recorder():
        """测试录制器"""

        def on_audio_data(data: bytes):
            print(f"收到音频数据: {len(data)} 字节")

        def on_started():
            print("录音开始")

        def on_stopped():
            print("录音停止")

        def on_error(error: str):
            print(f"录音错误: {error}")

        # 创建录制器
        recorder = await create_speech_recorder()
        if not recorder:
            print("创建录制器失败")
            return

        # 设置回调
        recorder.set_audio_callback(on_audio_data)
        recorder.set_status_callbacks(on_started, on_stopped, on_error)

        # 开始录音
        if await recorder.start_recording():
            print("录音5秒...")
            await asyncio.sleep(5)

            # 停止录音
            await recorder.stop_recording()

        # 关闭录制器
        await recorder.close()

    # 运行测试
    asyncio.run(test_recorder())