"""
PocketSpeak AI响应接收与解析模块

负责：
1. 监听WebSocket连接中的AI响应消息
2. 解析不同类型的消息（文本、音频、指令等）
3. 提取AI回复的文本内容和音频数据
4. 处理小智AI的MCP消息格式
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, Union, List
from dataclasses import dataclass
from enum import Enum
import base64

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"           # 纯文本消息
    AUDIO = "audio"         # 音频消息
    MCP = "mcp"            # MCP协议消息
    TTS = "tts"            # TTS语音合成消息
    EMOJI = "emoji"        # Emoji表情消息(AI回复结束标志)
    ERROR = "error"        # 错误消息
    UNKNOWN = "unknown"    # 未知消息类型


@dataclass
class AudioData:
    """音频数据结构"""
    data: bytes            # OPUS编码的音频数据
    format: str = "opus"   # 音频格式
    sample_rate: int = 24000  # 采样率
    channels: int = 1      # 声道数

    @property
    def size(self) -> int:
        """返回音频数据的字节大小"""
        return len(self.data)


@dataclass
class AIResponse:
    """AI响应数据结构"""
    message_type: MessageType
    text_content: Optional[str] = None     # 文本内容
    audio_data: Optional[AudioData] = None # 音频数据
    raw_message: Optional[Dict] = None     # 原始消息
    timestamp: Optional[str] = None        # 时间戳
    conversation_id: Optional[str] = None  # 会话ID


class AIResponseParser:
    """
    AI响应解析器

    功能：
    1. 解析WebSocket接收的消息
    2. 识别消息类型和内容
    3. 提取文本和音频数据
    4. 处理小智AI特定的消息格式
    """

    def __init__(self):
        """初始化AI响应解析器"""
        # 消息处理回调
        self.on_text_received: Optional[Callable[[str], None]] = None
        self.on_audio_received: Optional[Callable[[AudioData], None]] = None
        self.on_response_parsed: Optional[Callable[[AIResponse], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # 解析统计
        self.stats = {
            "total_messages": 0,
            "text_messages": 0,
            "audio_messages": 0,
            "mcp_messages": 0,
            "error_messages": 0,
            "unknown_messages": 0
        }

        logger.info("AI响应解析器初始化完成")

    def parse_message(self, raw_message: Union[str, bytes, Dict]) -> Optional[AIResponse]:
        """
        解析收到的消息

        Args:
            raw_message: 原始消息数据

        Returns:
            AIResponse: 解析后的响应对象，解析失败时返回None
        """
        try:
            self.stats["total_messages"] += 1

            # 预处理消息格式
            message_dict = self._preprocess_message(raw_message)
            if not message_dict:
                return None

            # 识别消息类型
            message_type = self._identify_message_type(message_dict)

            # 创建基础响应对象
            response = AIResponse(
                message_type=message_type,
                raw_message=message_dict,
                timestamp=message_dict.get("timestamp"),
                conversation_id=message_dict.get("conversation_id")
            )

            # 根据消息类型解析内容
            if message_type == MessageType.TEXT:
                self._parse_text_message(message_dict, response)
                self.stats["text_messages"] += 1

            elif message_type == MessageType.AUDIO:
                self._parse_audio_message(message_dict, response)
                self.stats["audio_messages"] += 1

            elif message_type == MessageType.EMOJI:
                self._parse_emoji_message(message_dict, response)
                logger.info(f"😊 收到Emoji消息 (AI回复结束标志): {message_dict.get('text')} - {message_dict.get('emotion')}")

            elif message_type == MessageType.MCP:
                self._parse_mcp_message(message_dict, response)
                self.stats["mcp_messages"] += 1

            elif message_type == MessageType.TTS:
                self._parse_tts_message(message_dict, response)
                self.stats["audio_messages"] += 1

            elif message_type == MessageType.ERROR:
                self._parse_error_message(message_dict, response)
                self.stats["error_messages"] += 1

            else:
                self.stats["unknown_messages"] += 1
                logger.warning(f"未知消息类型: {message_dict}")

            # 触发回调
            self._trigger_callbacks(response)

            return response

        except Exception as e:
            error_msg = f"解析消息失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return None

    def _preprocess_message(self, raw_message: Union[str, bytes, Dict]) -> Optional[Dict]:
        """
        预处理消息格式

        Args:
            raw_message: 原始消息

        Returns:
            Dict: 处理后的消息字典
        """
        try:
            # 如果已经是字典，直接返回
            if isinstance(raw_message, dict):
                return raw_message

            # 如果是字符串，尝试JSON解析
            if isinstance(raw_message, str):
                return json.loads(raw_message)

            # 如果是字节，先解码再JSON解析
            if isinstance(raw_message, bytes):
                return json.loads(raw_message.decode('utf-8'))

            logger.warning(f"不支持的消息格式: {type(raw_message)}")
            return None

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"消息预处理失败: {e}")
            return None

    def _identify_message_type(self, message: Dict) -> MessageType:
        """
        识别消息类型

        Args:
            message: 消息字典

        Returns:
            MessageType: 消息类型
        """
        # 检查是否有错误字段
        if "error" in message or message.get("type") == "error":
            return MessageType.ERROR

        # 检查是否为Emoji消息(AI回复结束标志)
        if self._is_emoji_message(message):
            return MessageType.EMOJI

        # 检查是否为MCP消息
        if self._is_mcp_message(message):
            return MessageType.MCP

        # 检查是否为TTS消息
        if self._is_tts_message(message):
            return MessageType.TTS

        # 检查是否为音频消息
        if self._is_audio_message(message):
            return MessageType.AUDIO

        # 检查是否为文本消息
        if self._is_text_message(message):
            return MessageType.TEXT

        return MessageType.UNKNOWN

    def _is_emoji_message(self, message: Dict) -> bool:
        """
        检查是否为Emoji消息(AI回复结束标志)
        格式: {"type":"llm", "text": "😊", "emotion": "smile"}
        """
        return (
            message.get("type") == "llm" and
            "emotion" in message and
            "text" in message
        )

    def _is_mcp_message(self, message: Dict) -> bool:
        """检查是否为MCP消息"""
        return (
            message.get("type") == "mcp" or
            "mcp" in message or
            ("content" in message and isinstance(message["content"], dict))
        )

    def _is_tts_message(self, message: Dict) -> bool:
        """
        检查是否为TTS消息
        包括TTS音频数据和TTS stop信号
        """
        return (
            message.get("type") == "tts" or
            message.get("action") == "tts" or
            ("audio_data" in message and "text" in message)
        )

    def _is_audio_message(self, message: Dict) -> bool:
        """检查是否为音频消息"""
        return (
            message.get("type") == "audio" or
            "audio_data" in message or
            "opus_data" in message or
            ("data" in message and message.get("format") in ["opus", "audio"])
        )

    def _is_text_message(self, message: Dict) -> bool:
        """检查是否为文本消息"""
        return (
            message.get("type") == "text" or
            "text" in message or
            "content" in message or
            "message" in message
        )

    def _parse_text_message(self, message: Dict, response: AIResponse):
        """解析文本消息"""
        # 提取文本内容
        text_content = (
            message.get("text") or
            message.get("content") or
            message.get("message") or
            message.get("data", {}).get("text") if isinstance(message.get("data"), dict) else None
        )

        if text_content:
            response.text_content = str(text_content)

    def _parse_audio_message(self, message: Dict, response: AIResponse):
        """解析音频消息"""
        try:
            # 提取音频数据
            audio_data = (
                message.get("audio_data") or
                message.get("opus_data") or
                message.get("data")
            )

            if audio_data:
                # 如果是base64编码的字符串，需要解码
                if isinstance(audio_data, str):
                    audio_bytes = base64.b64decode(audio_data)
                elif isinstance(audio_data, bytes):
                    audio_bytes = audio_data
                else:
                    logger.warning("无法识别的音频数据格式")
                    return

                # 创建音频数据对象
                response.audio_data = AudioData(
                    data=audio_bytes,
                    format=message.get("format", "opus"),
                    sample_rate=message.get("sample_rate", 24000),
                    channels=message.get("channels", 1)
                )

                # 同时提取可能的文本内容
                if "text" in message:
                    response.text_content = message["text"]

        except Exception as e:
            logger.error(f"解析音频数据失败: {e}")

    def _parse_emoji_message(self, message: Dict, response: AIResponse):
        """
        解析Emoji消息(AI回复结束标志)
        格式: {"type":"llm", "text": "😊", "emotion": "smile"}
        """
        try:
            # 提取emoji和情感
            emoji = message.get("text", "")
            emotion = message.get("emotion", "")

            # 将emoji和emotion保存到metadata
            if not response.raw_message:
                response.raw_message = {}
            response.raw_message["emoji"] = emoji
            response.raw_message["emotion"] = emotion

            logger.debug(f"解析Emoji消息: {emoji} ({emotion})")
        except Exception as e:
            logger.error(f"解析Emoji消息失败: {e}")

    def _parse_mcp_message(self, message: Dict, response: AIResponse):
        """解析MCP消息"""
        try:
            # MCP消息可能包含多种内容
            mcp_content = message.get("mcp") or message.get("content") or message

            # 提取文本内容
            if isinstance(mcp_content, dict):
                text_content = (
                    mcp_content.get("text") or
                    mcp_content.get("response") or
                    mcp_content.get("content")
                )
                if text_content:
                    response.text_content = str(text_content)

                # 检查是否包含音频数据
                if "audio" in mcp_content or "audio_data" in mcp_content:
                    self._parse_audio_message(mcp_content, response)

        except Exception as e:
            logger.error(f"解析MCP消息失败: {e}")

    def _parse_tts_message(self, message: Dict, response: AIResponse):
        """
        解析TTS消息
        支持两种类型:
        1. TTS音频数据: {"type": "tts", "audio_data": "...", "text": "..."}
        2. TTS stop信号: {"type": "tts", "state": "stop"}
        """
        try:
            # 检查是否为TTS stop信号(音频播放完成标志)
            if message.get("state") == "stop":
                logger.info("🛑 收到TTS stop信号 (音频播放完成标志)")
                # 在metadata中标记这是stop信号
                if not response.raw_message:
                    response.raw_message = {}
                response.raw_message["tts_stop"] = True
                return

            # 普通TTS消息：包含文本和音频
            response.text_content = message.get("text")

            # 解析音频数据
            self._parse_audio_message(message, response)

        except Exception as e:
            logger.error(f"解析TTS消息失败: {e}")

    def _parse_error_message(self, message: Dict, response: AIResponse):
        """解析错误消息"""
        error_content = (
            message.get("error") or
            message.get("error_message") or
            message.get("message") or
            "未知错误"
        )
        response.text_content = f"错误: {error_content}"

    def _trigger_callbacks(self, response: AIResponse):
        """触发相应的回调函数"""
        try:
            # 通用响应回调
            if self.on_response_parsed:
                self.on_response_parsed(response)

            # 文本内容回调
            if response.text_content and self.on_text_received:
                self.on_text_received(response.text_content)

            # 音频数据回调
            if response.audio_data and self.on_audio_received:
                self.on_audio_received(response.audio_data)

        except Exception as e:
            logger.error(f"触发回调失败: {e}")

    def set_callbacks(self,
                     on_text: Optional[Callable[[str], None]] = None,
                     on_audio: Optional[Callable[[AudioData], None]] = None,
                     on_response: Optional[Callable[[AIResponse], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """
        设置回调函数

        Args:
            on_text: 文本接收回调
            on_audio: 音频接收回调
            on_response: 响应解析回调
            on_error: 错误回调
        """
        self.on_text_received = on_text
        self.on_audio_received = on_audio
        self.on_response_parsed = on_response
        self.on_error = on_error
        logger.info("设置回调函数")

    def get_parsing_stats(self) -> Dict[str, Any]:
        """
        获取解析统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            "total_messages": self.stats["total_messages"],
            "text_messages": self.stats["text_messages"],
            "audio_messages": self.stats["audio_messages"],
            "mcp_messages": self.stats["mcp_messages"],
            "error_messages": self.stats["error_messages"],
            "unknown_messages": self.stats["unknown_messages"],
            "success_rate": (
                (self.stats["total_messages"] - self.stats["unknown_messages"]) /
                max(self.stats["total_messages"], 1) * 100
            )
        }

    def reset_stats(self):
        """重置统计信息"""
        for key in self.stats:
            self.stats[key] = 0
        logger.info("重置解析统计")


# 便捷函数
def create_ai_response_parser() -> AIResponseParser:
    """
    创建AI响应解析器

    Returns:
        AIResponseParser: 解析器实例
    """
    return AIResponseParser()


# 示例使用
if __name__ == "__main__":
    def on_text_received(text: str):
        print(f"收到文本: {text}")

    def on_audio_received(audio: AudioData):
        print(f"收到音频: {len(audio.data)} 字节, 格式: {audio.format}")

    def on_response_parsed(response: AIResponse):
        print(f"解析响应: 类型={response.message_type.value}")

    def on_error(error: str):
        print(f"解析错误: {error}")

    # 创建解析器
    parser = create_ai_response_parser()

    # 设置回调
    parser.set_callbacks(
        on_text=on_text_received,
        on_audio=on_audio_received,
        on_response=on_response_parsed,
        on_error=on_error
    )

    # 测试不同类型的消息
    test_messages = [
        # 文本消息
        {"type": "text", "content": "你好，我是AI助手"},

        # 音频消息
        {"type": "audio", "audio_data": "dGVzdCBhdWRpbyBkYXRh", "format": "opus"},

        # MCP消息
        {"type": "mcp", "content": {"text": "这是MCP响应", "audio": "YXVkaW8gZGF0YQ=="}},

        # 错误消息
        {"type": "error", "error": "请求处理失败"}
    ]

    for i, message in enumerate(test_messages):
        print(f"\n测试消息 {i+1}:")
        response = parser.parse_message(message)
        if response:
            print(f"  - 类型: {response.message_type.value}")
            if response.text_content:
                print(f"  - 文本: {response.text_content}")
            if response.audio_data:
                print(f"  - 音频: {len(response.audio_data.data)} 字节")

    print(f"\n解析统计: {parser.get_parsing_stats()}")