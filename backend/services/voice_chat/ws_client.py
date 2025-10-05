"""
PocketSpeak WebSocket 客户端管理模块

负责与小智AI官方服务器建立和维护WebSocket连接
基于py-xiaozhi的架构实现设备认证、心跳维护和断线重连功能
"""

import asyncio
import json
import logging
import time
import random
from typing import Optional, Callable, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import websockets
import ssl
from pathlib import Path

# 导入设备管理相关模块
from services.device_lifecycle import PocketSpeakDeviceManager, DeviceInfo

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


@dataclass
class WSConfig:
    """WebSocket连接配置"""
    url: str = "wss://api.tenclass.net/xiaozhi/v1/"
    ping_interval: int = 30  # 心跳间隔（秒）
    ping_timeout: int = 10   # 心跳超时（秒）
    max_reconnect_attempts: int = 10
    reconnect_base_delay: float = 1.0  # 基础重连延迟
    reconnect_max_delay: float = 60.0  # 最大重连延迟
    connection_timeout: int = 30


@dataclass
class AuthPayload:
    """认证载荷数据结构"""
    device_id: str
    serial_number: str
    client_id: str
    timestamp: int
    token: Optional[str] = None


class XiaozhiWebSocketClient:
    """
    小智AI WebSocket客户端

    功能：
    1. 建立与xiaozhi服务器的WebSocket连接
    2. 处理设备认证和hello确认
    3. 实现心跳机制维持连接
    4. 自动断线重连（exponential backoff）
    5. 提供消息发送和接收接口
    """

    def __init__(self, config: Optional[WSConfig] = None, device_manager: Optional[PocketSpeakDeviceManager] = None):
        """
        初始化WebSocket客户端

        Args:
            config: WebSocket连接配置
            device_manager: 设备管理器实例
        """
        self.config = config or WSConfig()
        self.device_manager = device_manager

        # 连接状态管理
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # 重连控制
        self.reconnect_attempts = 0
        self.should_reconnect = True

        # 设备信息缓存
        self.device_info: Optional[DeviceInfo] = None

        # 会话ID（服务器hello响应中返回）
        self.session_id: str = ""

        # 回调函数
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_authenticated: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[str], None]] = None
        self.on_message_received: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # 统计信息
        self.stats = {
            "total_connections": 0,
            "successful_auths": 0,
            "reconnect_count": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "last_connected": None,
            "uptime_start": None
        }

        logger.info("XiaozhiWebSocketClient 初始化完成")

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            bool: 连接是否成功
        """
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
            logger.warning("WebSocket连接已存在或正在连接中")
            return True

        try:
            logger.info(f"开始连接到小智AI服务器: {self.config.url}")
            self.state = ConnectionState.CONNECTING
            self.stats["total_connections"] += 1

            # 准备设备信息
            if not await self._prepare_device_info():
                return False

            # 创建SSL上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 准备HTTP Headers（参照py-xiaozhi的协议）
            # 从connection_params获取access_token
            connection_params = getattr(self.device_info, 'connection_params', {})
            websocket_params = connection_params.get('websocket', {})
            access_token = websocket_params.get('token', 'test-token')

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Protocol-Version": "1",
                "Device-Id": self.device_info.device_id,
                "Client-Id": self.device_info.client_id,
            }

            logger.info(f"📋 WebSocket连接Headers: Device-Id={self.device_info.device_id}")

            # 建立WebSocket连接（带认证Headers）
            try:
                # 新版本websockets写法
                self.websocket = await websockets.connect(
                    uri=self.config.url,
                    ssl=ssl_context,
                    additional_headers=headers,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024,  # 最大消息10MB
                    compression=None  # 禁用压缩
                )
            except TypeError:
                # 旧版本websockets写法
                self.websocket = await websockets.connect(
                    self.config.url,
                    ssl=ssl_context,
                    extra_headers=headers,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024,
                    compression=None
                )

            self.state = ConnectionState.CONNECTED
            self.stats["last_connected"] = time.time()
            self.stats["uptime_start"] = time.time()
            self.reconnect_attempts = 0

            logger.info("✅ WebSocket连接建立成功")

            if self.on_connected:
                self.on_connected()

            # 启动消息处理和心跳任务
            self.connection_task = asyncio.create_task(self._handle_messages())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 发送认证消息
            await self._authenticate()

            return True

        except Exception as e:
            error_msg = f"WebSocket连接失败: {e}"
            logger.error(error_msg)
            self.state = ConnectionState.ERROR

            if self.on_error:
                self.on_error(error_msg)

            # 自动重连
            if self.should_reconnect:
                await self._schedule_reconnect()

            return False

    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("开始断开WebSocket连接")

        self.should_reconnect = False
        self.state = ConnectionState.DISCONNECTED

        # 取消任务
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭WebSocket连接
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        logger.info("✅ WebSocket连接已断开")

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        发送消息到WebSocket服务器

        Args:
            message: 要发送的消息字典

        Returns:
            bool: 发送是否成功
        """
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning("WebSocket未认证，无法发送消息")
            return False

        if not self.websocket:
            logger.error("WebSocket连接不存在")
            return False

        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_json)
            self.stats["messages_sent"] += 1

            logger.debug(f"📤 发送消息: {message_json}")
            return True

        except Exception as e:
            error_msg = f"发送消息失败: {e}"
            logger.error(error_msg)

            if self.on_error:
                self.on_error(error_msg)

            return False

    async def send_start_listening(self, mode: str = "auto") -> bool:
        """
        发送开始监听消息（遵循py-xiaozhi协议）

        Args:
            mode: 监听模式，可选值：
                - "auto": AUTO_STOP模式（回合制对话）
                - "manual": 手动按压模式
                - "realtime": 实时对话模式（需要AEC）

        Returns:
            bool: 发送是否成功
        """
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning("WebSocket未认证，无法发送开始监听消息")
            return False

        if not self.session_id:
            logger.error("Session ID为空，无法发送开始监听消息")
            return False

        try:
            # 构造开始监听消息（参照py-xiaozhi协议）
            message = {
                "session_id": self.session_id,
                "type": "listen",
                "state": "start",
                "mode": mode
            }

            message_json = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_json)

            logger.info(f"📤 发送开始监听消息: mode={mode}, session_id={self.session_id}")
            return True

        except Exception as e:
            error_msg = f"发送开始监听消息失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

    async def send_stop_listening(self) -> bool:
        """
        发送停止监听消息（遵循py-xiaozhi协议）

        Returns:
            bool: 发送是否成功
        """
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning("WebSocket未认证，无法发送停止监听消息")
            return False

        if not self.session_id:
            logger.error("Session ID为空，无法发送停止监听消息")
            return False

        try:
            # 构造停止监听消息（参照py-xiaozhi协议）
            message = {
                "session_id": self.session_id,
                "type": "listen",
                "state": "stop"
            }

            message_json = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_json)

            logger.info(f"📤 发送停止监听消息: session_id={self.session_id}")
            return True

        except Exception as e:
            error_msg = f"发送停止监听消息失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

    async def send_audio(self, audio_data: bytes) -> bool:
        """
        发送音频数据到WebSocket服务器

        Args:
            audio_data: OPUS编码的音频数据

        Returns:
            bool: 发送是否成功
        """
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning("WebSocket未认证，无法发送音频")
            return False

        if not self.websocket:
            logger.error("WebSocket连接不存在")
            return False

        try:
            # 发送二进制音频数据
            await self.websocket.send(audio_data)
            self.stats["messages_sent"] += 1

            logger.debug(f"📤 发送音频数据: {len(audio_data)} bytes")
            return True

        except Exception as e:
            error_msg = f"发送音频数据失败: {e}"
            logger.error(error_msg)

            if self.on_error:
                self.on_error(error_msg)

            return False

    async def _prepare_device_info(self) -> bool:
        """准备设备信息用于认证"""
        if not self.device_manager:
            logger.error("设备管理器未初始化")
            return False

        try:
            # 获取设备身份信息
            serial_number, hmac_key, device_id = self.device_manager.ensure_device_identity()

            # 从设备生命周期管理器获取设备信息
            device_info = self.device_manager.lifecycle_manager.load_device_info_from_local()
            if device_info:
                # load_device_info_from_local() 已经返回 DeviceInfo 对象，直接使用
                self.device_info = device_info
                logger.info(f"📱 设备信息已加载: {device_id}")
                return True
            else:
                logger.error("设备信息加载失败")
                return False

        except Exception as e:
            logger.error(f"准备设备信息失败: {e}")
            return False

    async def _authenticate(self):
        """
        发送hello握手消息（遵循py-xiaozhi的WebSocket协议）
        参考: py-xiaozhi/src/protocols/websocket_protocol.py
        """
        if not self.device_info:
            logger.error("设备信息不可用，无法发送hello消息")
            return

        try:
            # 构造hello消息（参照py-xiaozhi的格式）
            hello_message = {
                "type": "hello",
                "version": 1,
                "features": {
                    "mcp": True,  # 支持MCP协议
                },
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,  # AudioConfig.INPUT_SAMPLE_RATE
                    "channels": 1,         # AudioConfig.CHANNELS
                    "frame_duration": 40,  # AudioConfig.FRAME_DURATION (ms)
                }
            }

            # 发送hello消息
            message_json = json.dumps(hello_message, ensure_ascii=False)
            await self.websocket.send(message_json)

            logger.info(f"📤 发送hello握手消息: device={self.device_info.device_id}")

        except Exception as e:
            error_msg = f"发送hello消息失败: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)

    async def _handle_messages(self):
        """处理接收到的WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    if isinstance(message, str):
                        # 文本消息 - JSON格式
                        data = json.loads(message)
                        self.stats["messages_received"] += 1

                        logger.debug(f"📥 收到JSON消息: {message[:200]}...")

                        # 处理不同类型的消息
                        await self._process_message(data)

                        # 触发消息接收回调
                        if self.on_message_received:
                            self.on_message_received(data)

                    elif isinstance(message, bytes):
                        # 二进制消息 - OPUS音频数据
                        self.stats["messages_received"] += 1
                        logger.info(f"📥 收到二进制音频数据: {len(message)} bytes")

                        # 触发音频接收回调
                        if self.on_message_received:
                            # 将音频包装成消息格式传递给解析器
                            audio_message = {
                                "type": "audio",
                                "format": "opus",
                                "sample_rate": 24000,
                                "channels": 1,
                                "data": message  # 原始二进制数据
                            }
                            logger.info(f"📤 传递音频消息给解析器: type={audio_message['type']}, format={audio_message['format']}, size={len(message)} bytes")
                            self.on_message_received(audio_message)

                except json.JSONDecodeError as e:
                    logger.warning(f"解析消息JSON失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}", exc_info=True)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            self.state = ConnectionState.DISCONNECTED

            if self.on_disconnected:
                self.on_disconnected("连接关闭")

            # 自动重连
            if self.should_reconnect:
                await self._schedule_reconnect()

        except Exception as e:
            error_msg = f"消息处理循环异常: {e}"
            logger.error(error_msg)
            self.state = ConnectionState.ERROR

            if self.on_error:
                self.on_error(error_msg)

    async def _process_message(self, data: Dict[str, Any]):
        """处理特定类型的消息"""
        message_type = data.get("type")

        if message_type == "hello":
            # 处理hello确认消息
            # 提取session_id（参照py-xiaozhi协议）
            session_id = data.get("session_id")
            if session_id:
                self.session_id = session_id
                logger.info(f"✅ 收到服务器hello确认, session_id={session_id}")
            else:
                logger.warning("⚠️ 服务器hello响应中没有session_id")
                logger.info("✅ 收到服务器hello确认")

            self.state = ConnectionState.AUTHENTICATED
            self.stats["successful_auths"] += 1

            if self.on_authenticated:
                self.on_authenticated()

        elif message_type == "auth_response":
            # 处理认证响应
            success = data.get("success", False)
            if success:
                logger.info("✅ 设备认证成功")
                self.state = ConnectionState.AUTHENTICATED
                self.stats["successful_auths"] += 1

                if self.on_authenticated:
                    self.on_authenticated()
            else:
                error_msg = data.get("message", "认证失败")
                logger.error(f"❌ 设备认证失败: {error_msg}")

        elif message_type == "pong":
            # 处理心跳响应
            logger.debug("💓 收到心跳pong响应")

        elif message_type == "error":
            # 处理错误消息
            error_msg = data.get("message", "服务器错误")
            logger.error(f"❌ 服务器错误: {error_msg}")

            if self.on_error:
                self.on_error(f"服务器错误: {error_msg}")

    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
                await asyncio.sleep(self.config.ping_interval)

                if self.websocket and not self.websocket.closed:
                    try:
                        # 发送心跳ping消息
                        ping_message = {
                            "type": "ping",
                            "timestamp": int(time.time())
                        }

                        message_json = json.dumps(ping_message)
                        await self.websocket.send(message_json)

                        logger.debug("💓 发送心跳ping")

                    except Exception as e:
                        logger.warning(f"发送心跳失败: {e}")
                        break

        except asyncio.CancelledError:
            logger.debug("心跳任务已取消")

    async def _schedule_reconnect(self):
        """调度重连（指数退避）"""
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("达到最大重连次数，停止重连")
            return

        # 计算重连延迟（指数退避）
        delay = min(
            self.config.reconnect_base_delay * (2 ** self.reconnect_attempts),
            self.config.reconnect_max_delay
        )

        # 添加随机抖动
        jitter = random.uniform(0, delay * 0.1)
        total_delay = delay + jitter

        self.reconnect_attempts += 1
        self.stats["reconnect_count"] += 1

        logger.info(f"🔄 将在 {total_delay:.1f} 秒后尝试第 {self.reconnect_attempts} 次重连")

        await asyncio.sleep(total_delay)

        if self.should_reconnect:
            await self.connect()

    def set_callbacks(self,
                     on_connected: Optional[Callable[[], None]] = None,
                     on_authenticated: Optional[Callable[[], None]] = None,
                     on_disconnected: Optional[Callable[[str], None]] = None,
                     on_message_received: Optional[Callable[[Dict[str, Any]], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """
        设置回调函数

        Args:
            on_connected: 连接建立回调
            on_authenticated: 认证成功回调
            on_disconnected: 连接断开回调
            on_message_received: 消息接收回调
            on_error: 错误回调
        """
        self.on_connected = on_connected
        self.on_authenticated = on_authenticated
        self.on_disconnected = on_disconnected
        self.on_message_received = on_message_received
        self.on_error = on_error

        logger.info("WebSocket回调函数已设置")

    def get_connection_status(self) -> Dict[str, Any]:
        """
        获取连接状态信息

        Returns:
            Dict: 状态信息
        """
        uptime = None
        if self.stats["uptime_start"]:
            uptime = time.time() - self.stats["uptime_start"]

        return {
            "state": self.state.value,
            "connected": self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED],
            "authenticated": self.state == ConnectionState.AUTHENTICATED,
            "reconnect_attempts": self.reconnect_attempts,
            "should_reconnect": self.should_reconnect,
            "device_info": {
                "device_id": self.device_info.device_id if self.device_info else None,
                "activated": self.device_info.activated if self.device_info else False
            } if self.device_info else None,
            "config": {
                "url": self.config.url,
                "ping_interval": self.config.ping_interval,
                "max_reconnect_attempts": self.config.max_reconnect_attempts
            },
            "stats": {
                **self.stats,
                "uptime": uptime
            }
        }

    async def close(self):
        """关闭WebSocket客户端并释放资源"""
        logger.info("关闭WebSocket客户端")
        await self.disconnect()


# 全局WebSocket客户端实例
_ws_client: Optional[XiaozhiWebSocketClient] = None


async def get_websocket_client(device_manager: Optional[PocketSpeakDeviceManager] = None) -> XiaozhiWebSocketClient:
    """
    获取全局WebSocket客户端实例

    Args:
        device_manager: 设备管理器实例

    Returns:
        XiaozhiWebSocketClient: WebSocket客户端实例
    """
    global _ws_client

    if _ws_client is None:
        _ws_client = XiaozhiWebSocketClient(device_manager=device_manager)
        logger.info("创建新的WebSocket客户端实例")

    return _ws_client


async def initialize_websocket_connection(device_manager: PocketSpeakDeviceManager) -> bool:
    """
    初始化并启动WebSocket连接

    Args:
        device_manager: 设备管理器实例

    Returns:
        bool: 初始化是否成功
    """
    try:
        client = await get_websocket_client(device_manager)

        # 设置回调函数
        def on_connected():
            logger.info("🎉 WebSocket连接已建立")

        def on_authenticated():
            logger.info("🔐 WebSocket认证成功，可以进行语音通信")

        def on_disconnected(reason: str):
            logger.warning(f"⚠️ WebSocket连接断开: {reason}")

        def on_message_received(message: Dict[str, Any]):
            logger.info(f"📨 收到WebSocket消息: {message.get('type', 'unknown')}")

        def on_error(error: str):
            logger.error(f"❌ WebSocket错误: {error}")

        client.set_callbacks(
            on_connected=on_connected,
            on_authenticated=on_authenticated,
            on_disconnected=on_disconnected,
            on_message_received=on_message_received,
            on_error=on_error
        )

        # 启动连接
        success = await client.connect()

        if success:
            logger.info("✅ WebSocket连接初始化成功")
        else:
            logger.error("❌ WebSocket连接初始化失败")

        return success

    except Exception as e:
        logger.error(f"WebSocket连接初始化异常: {e}")
        return False


# 便捷函数
async def send_voice_message(audio_data: bytes, format: str = "opus") -> bool:
    """
    发送语音消息到小智AI

    Args:
        audio_data: 音频数据
        format: 音频格式

    Returns:
        bool: 发送是否成功
    """
    client = await get_websocket_client()

    if client.state != ConnectionState.AUTHENTICATED:
        logger.warning("WebSocket未认证，无法发送语音消息")
        return False

    # 构造语音消息
    voice_message = {
        "type": "voice",
        "action": "send_audio",
        "data": {
            "audio": audio_data.hex(),  # 转换为十六进制字符串
            "format": format,
            "timestamp": int(time.time())
        }
    }

    return await client.send_message(voice_message)


async def get_connection_status() -> Dict[str, Any]:
    """获取WebSocket连接状态"""
    client = await get_websocket_client()
    return client.get_connection_status()


# 示例使用
if __name__ == "__main__":
    async def test_websocket():
        """测试WebSocket连接"""
        # 这里需要真实的设备管理器实例
        # device_manager = PocketSpeakDeviceManager(lifecycle_manager)
        # success = await initialize_websocket_connection(device_manager)

        print("WebSocket客户端测试完成")

    # 运行测试
    asyncio.run(test_websocket())