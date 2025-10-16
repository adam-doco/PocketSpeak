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
    ping_interval: int = 20  # 心跳间隔（秒）- 对齐py-xiaozhi的生产验证值
    ping_timeout: int = 20   # 心跳超时（秒）- 对齐py-xiaozhi的生产验证值
    max_reconnect_attempts: int = 10
    reconnect_base_delay: float = 1.0  # 基础重连延迟
    reconnect_max_delay: float = 60.0  # 最大重连延迟
    connection_timeout: int = 30
    monitor_interval: int = 5  # 连接监控间隔（秒）- 参照py-xiaozhi


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
        self.heartbeat_task: Optional[asyncio.Task] = None  # 已弃用，保留兼容性
        self.monitor_task: Optional[asyncio.Task] = None  # 连接监控任务（参照py-xiaozhi）

        # 重连控制
        self.reconnect_attempts = 0
        self.should_reconnect = True
        self._is_closing = False  # 是否正在主动关闭（参照py-xiaozhi）
        self._auto_reconnect_enabled = False  # 自动重连开关（参照py-xiaozhi）
        self._max_reconnect_attempts = 0  # 最大重连次数（参照py-xiaozhi）

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

            logger.info(f"✅ WebSocket连接建立成功 (ping_interval={self.config.ping_interval}s, ping_timeout={self.config.ping_timeout}s)")

            if self.on_connected:
                self.on_connected()

            # 启动消息处理任务
            self.connection_task = asyncio.create_task(self._handle_messages())
            # 🔥 禁用自定义应用层心跳任务，使用websockets库内置的ping/pong机制（参照py-xiaozhi）
            # self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("💓 使用websockets库内置心跳机制（无需应用层心跳任务）")

            # 🔥 启动连接监控任务（每5秒检查连接状态，参照py-xiaozhi）
            self.monitor_task = asyncio.create_task(self._connection_monitor())
            logger.info(f"🔍 连接监控任务已启动 (检查间隔={self.config.monitor_interval}s)")

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

    def enable_auto_reconnect(self, enabled: bool = True, max_attempts: int = 5):
        """
        启用或禁用自动重连功能（参照py-xiaozhi）

        Args:
            enabled: 是否启用自动重连
            max_attempts: 最大重连次数（仅当enabled=True时有效）
        """
        self._auto_reconnect_enabled = enabled
        if enabled:
            self._max_reconnect_attempts = max_attempts
            logger.info(f"✅ 启用自动重连，最大尝试次数: {max_attempts}")
        else:
            self._max_reconnect_attempts = 0
            logger.info("❌ 禁用自动重连")

    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("开始断开WebSocket连接")

        self.should_reconnect = False
        self._is_closing = True  # 标记为主动关闭（参照py-xiaozhi）
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

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
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

        if not self.websocket or self.websocket.closed:
            logger.error("WebSocket连接不存在或已关闭，无法发送开始监听消息")
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

            # 临时调试：记录开始监听时间点
            import time
            self._listening_start_time = time.time()
            # 重置音频帧计数（用于追踪本轮对话）
            self._audio_frames_this_session = 0

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

        if not self.websocket or self.websocket.closed:
            logger.error("WebSocket连接不存在或已关闭，无法发送停止监听消息")
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

            # 临时调试：统计本轮发送的音频
            import time
            total_frames = getattr(self, '_audio_frames_this_session', 0)
            if hasattr(self, '_listening_start_time'):
                duration = (time.time() - self._listening_start_time) * 1000
                logger.info(f"📤 发送停止监听消息 | 本轮统计: 共发送 {total_frames} 帧音频, 录音时长: {duration:.0f}ms")
            else:
                logger.info(f"📤 发送停止监听消息 | 本轮统计: 共发送 {total_frames} 帧音频")

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

            # 临时调试：追踪本轮对话的音频发送
            if not hasattr(self, '_audio_frames_this_session'):
                self._audio_frames_this_session = 0
            self._audio_frames_this_session += 1

            # 每10帧打印一次，验证音频是否实时发送
            if self._audio_frames_this_session % 10 == 0:
                import time
                if hasattr(self, '_listening_start_time'):
                    elapsed = (time.time() - self._listening_start_time) * 1000
                    logger.info(f"📤 [实时发送] 本轮已发送 {self._audio_frames_this_session} 帧 (+{len(audio_data)}B) | 录音进行中: {elapsed:.0f}ms")
                else:
                    logger.info(f"📤 [实时发送] 本轮已发送 {self._audio_frames_this_session} 帧 (+{len(audio_data)}B)")

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
                            self.on_message_received(audio_message)

                except json.JSONDecodeError as e:
                    logger.warning(f"解析消息JSON失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}", exc_info=True)

        except websockets.exceptions.ConnectionClosed as e:
            # WebSocket正常关闭（参照py-xiaozhi）
            close_code = getattr(e, 'code', 'unknown')
            close_reason = getattr(e, 'reason', 'unknown')
            logger.warning(f"WebSocket连接已关闭 (code={close_code}, reason={close_reason})")
            await self._handle_connection_loss(f"连接关闭: {close_code} {close_reason}")

        except websockets.exceptions.ConnectionClosedError as e:
            # WebSocket异常关闭（参照py-xiaozhi）
            close_code = getattr(e, 'code', 'unknown')
            close_reason = getattr(e, 'reason', 'unknown')
            logger.error(f"WebSocket连接错误: code={close_code}, reason={close_reason}")
            await self._handle_connection_loss(f"连接错误: {close_code} {close_reason}")

        except websockets.exceptions.InvalidState as e:
            # WebSocket状态异常（参照py-xiaozhi）
            logger.error(f"WebSocket状态异常: {e}")
            await self._handle_connection_loss("连接状态异常")

        except ConnectionResetError:
            # 连接被重置（参照py-xiaozhi）
            logger.error("连接被重置 (ConnectionResetError)")
            await self._handle_connection_loss("连接被重置")

        except OSError as e:
            # 网络I/O错误（参照py-xiaozhi）
            logger.error(f"网络I/O错误: {e}")
            await self._handle_connection_loss(f"网络I/O错误: {e}")

        except Exception as e:
            # 其他未预期的异常
            error_msg = f"消息处理循环异常: {e}"
            logger.error(error_msg, exc_info=True)
            await self._handle_connection_loss(f"未知异常: {e}")

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
        """
        心跳循环（已弃用）

        注意：此方法已被websockets库的内置ping/pong机制取代
        保留此方法仅为兼容性，实际不再使用
        """
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

    async def _connection_monitor(self):
        """
        连接监控任务（完全参照py-xiaozhi实现）

        每5秒检查一次WebSocket连接状态：
        1. 检查websocket对象是否存在
        2. 使用close_code检查连接是否真正关闭（不是closed属性！）
        3. 如果发现异常，触发连接丢失处理

        关键差异：
        - closed属性：只检查是否调用了close()方法
        - close_code属性：检查连接是否真正被关闭（包括服务器断开和网络异常）

        这是主动监控机制，配合websockets库的被动ping/pong形成双重保障
        """
        try:
            while self.websocket and not self.should_reconnect == False:
                await asyncio.sleep(self.config.monitor_interval)

                # 🔥 关键修复：使用close_code而不是closed（参照py-xiaozhi第219行）
                if self.websocket:
                    if self.websocket.close_code is not None:
                        logger.warning(f"🔍 连接监控：检测到WebSocket连接已关闭 (close_code={self.websocket.close_code})")
                        # 触发连接丢失处理
                        await self._handle_connection_loss("连接监控检测到连接已关闭")
                        break
                    else:
                        # 连接正常，记录调试信息
                        logger.debug(f"🔍 连接监控：连接正常 (close_code=None, state={self.state.value})")

        except asyncio.CancelledError:
            logger.debug("连接监控任务已取消")
        except Exception as e:
            logger.error(f"连接监控任务异常: {e}", exc_info=True)

    async def _cleanup_connection(self):
        """
        清理连接资源（参照py-xiaozhi实现）

        在重连之前必须彻底清理旧的连接和任务，避免资源泄漏
        """
        logger.debug("🧹 开始清理连接资源")

        # 取消所有后台任务
        tasks_to_cancel = []
        if self.connection_task and not self.connection_task.done():
            tasks_to_cancel.append(("connection_task", self.connection_task))
        if self.heartbeat_task and not self.heartbeat_task.done():
            tasks_to_cancel.append(("heartbeat_task", self.heartbeat_task))
        if self.monitor_task and not self.monitor_task.done():
            tasks_to_cancel.append(("monitor_task", self.monitor_task))

        # 取消任务
        for task_name, task in tasks_to_cancel:
            try:
                task.cancel()
                await asyncio.wait_for(task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.debug(f"✅ 已取消 {task_name}")
            except Exception as e:
                logger.warning(f"取消 {task_name} 失败: {e}")

        # 关闭WebSocket连接
        if self.websocket:
            try:
                await asyncio.wait_for(self.websocket.close(), timeout=2.0)
                logger.debug("✅ WebSocket连接已关闭")
            except asyncio.TimeoutError:
                logger.warning("WebSocket关闭超时")
            except Exception as e:
                logger.warning(f"关闭WebSocket失败: {e}")
            finally:
                self.websocket = None

        # 重置任务引用
        self.connection_task = None
        self.heartbeat_task = None
        self.monitor_task = None

        logger.debug("✅ 连接资源清理完成")

    async def _handle_connection_loss(self, reason: str):
        """
        处理连接丢失（参照py-xiaozhi实现）

        这个方法会：
        1. 检查是否正在主动关闭（避免不必要的重连）
        2. 清理连接资源
        3. 更新连接状态
        4. 触发断开回调
        5. 如果启用自动重连，触发重连
        """
        logger.warning(f"🔗 处理连接丢失: {reason}")

        # 🔥 检查是否正在主动关闭（参照py-xiaozhi）
        if self._is_closing:
            logger.info("正在主动关闭连接，跳过重连逻辑")
            return

        # 🔥 清理连接资源（参照py-xiaozhi）
        await self._cleanup_connection()

        # 更新连接状态
        was_connected = self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]
        self.state = ConnectionState.DISCONNECTED

        # 通知连接状态变化
        if self.on_disconnected and was_connected:
            try:
                self.on_disconnected(reason)
            except Exception as e:
                logger.error(f"调用连接断开回调失败: {e}")

        # 🔥 检查自动重连开关（参照py-xiaozhi）
        if self._auto_reconnect_enabled and self.should_reconnect:
            # 检查重连次数限制
            if self._max_reconnect_attempts > 0 and self.reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"已达到最大重连次数 ({self._max_reconnect_attempts})，停止重连")
                if self.on_error:
                    self.on_error(f"连接丢失且已达最大重连次数: {reason}")
            else:
                # 触发重连
                await self._schedule_reconnect()
        else:
            # 未启用自动重连或should_reconnect为False
            logger.info("自动重连未启用或已禁止重连")
            if self.on_error:
                self.on_error(f"连接丢失: {reason}")

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