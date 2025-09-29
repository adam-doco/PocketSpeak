"""
PocketSpeak 绑定确认轮询模块
负责轮询小智AI服务器获取设备绑定确认状态，直到收到成功响应

基于 py-xiaozhi 项目的设备激活流程实现
参考路径:
- backend/libs/py_xiaozhi/src/utils/device_activator.py 中的激活轮询逻辑
"""

import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import time

from core.device_manager import device_manager
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class BindStatusResult:
    """绑定状态查询结果"""
    success: bool
    is_activated: bool = False
    websocket_url: Optional[str] = None
    access_token: Optional[str] = None
    message: str = ""
    error_detail: Optional[str] = None
    activation_data: Optional[Dict[str, Any]] = None


class BindStatusListener:
    """绑定状态轮询器 - 监听小智AI服务器的绑定确认"""

    def __init__(self):
        """初始化绑定状态轮询器"""
        self.is_running = False
        self.activation_url = None
        self.request_headers = None
        self._polling_task: Optional[asyncio.Task] = None

        # 回调函数
        self.on_bind_confirmed: Optional[Callable[[BindStatusResult], None]] = None
        self.on_polling_error: Optional[Callable[[str], None]] = None
        self.on_polling_update: Optional[Callable[[str, int], None]] = None

        # 轮询配置
        self.retry_interval = 5  # 轮询间隔（秒）
        self.max_retries = 60   # 最大重试次数（5分钟）

        logger.info("初始化绑定状态轮询器")

    def _prepare_activation_request(self, challenge: str) -> Dict[str, Any]:
        """
        准备激活请求数据

        Args:
            challenge: 服务器发送的挑战字符串

        Returns:
            Dict: 激活请求数据
        """
        # 获取设备信息
        device_id = device_manager.generate_device_id()

        # 尝试使用py-xiaozhi的HMAC签名（如果可用）
        hmac_signature = None
        serial_number = None

        try:
            # 尝试获取序列号和HMAC签名
            serial_number = device_manager.get_serial_number()
            if serial_number and hasattr(device_manager, 'generate_hmac'):
                hmac_signature = device_manager.generate_hmac(challenge)
        except Exception as e:
            logger.debug(f"无法获取py-xiaozhi HMAC签名，使用备用方案: {e}")

        # 如果没有HMAC签名，使用设备ID作为备用
        if not hmac_signature:
            import hashlib
            hmac_signature = hashlib.sha256(f"{device_id}:{challenge}".encode()).hexdigest()

        if not serial_number:
            serial_number = device_id

        # 构建激活请求负载
        payload = {
            "Payload": {
                "algorithm": "hmac-sha256",
                "serial_number": serial_number,
                "challenge": challenge,
                "hmac": hmac_signature,
            }
        }

        return payload

    def _prepare_request_headers(self) -> Dict[str, str]:
        """准备请求头"""
        device_id = device_manager.generate_device_id()

        headers = {
            "Activation-Version": "2",
            "Device-Id": device_id,
            "Client-Id": "PocketSpeak-V1.0",
            "Content-Type": "application/json",
        }

        return headers

    async def start_polling(self, challenge: str, timeout: int = 300) -> BindStatusResult:
        """
        启动绑定状态轮询

        Args:
            challenge: 服务器发送的挑战字符串
            timeout: 总超时时间（秒）

        Returns:
            BindStatusResult: 轮询结果
        """
        if self.is_running:
            return BindStatusResult(
                success=False,
                message="轮询器已在运行中",
                error_detail="重复启动轮询器"
            )

        self.is_running = True

        try:
            logger.info("🔄 启动绑定状态轮询...")

            # 准备激活URL
            ota_url = settings.xiaozhi_ota_url
            if not ota_url.endswith("/"):
                ota_url += "/"
            self.activation_url = f"{ota_url}activate"

            # 准备请求数据和头部
            activation_payload = self._prepare_activation_request(challenge)
            self.request_headers = self._prepare_request_headers()

            logger.info(f"📡 激活URL: {self.activation_url}")
            logger.debug(f"请求头: {self.request_headers}")
            logger.debug(f"请求负载: {json.dumps(activation_payload, indent=2)}")

            # 启动轮询任务
            result = await self._poll_activation_status(activation_payload, timeout)

            return result

        except Exception as e:
            logger.error(f"轮询过程中发生异常: {e}")
            return BindStatusResult(
                success=False,
                message="轮询流程异常",
                error_detail=str(e)
            )
        finally:
            self.is_running = False

    async def _poll_activation_status(self, payload: Dict[str, Any], timeout: int) -> BindStatusResult:
        """
        执行激活状态轮询

        Args:
            payload: 激活请求负载
            timeout: 超时时间

        Returns:
            BindStatusResult: 轮询结果
        """
        start_time = time.time()
        retry_count = 0
        last_error = None

        # 创建HTTP会话
        timeout_config = aiohttp.ClientTimeout(total=10)  # 单次请求10秒超时

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            while retry_count < self.max_retries:
                # 检查总体超时
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    logger.warning(f"达到总体超时限制 ({timeout}秒)")
                    break

                retry_count += 1

                try:
                    logger.info(f"📊 轮询尝试 {retry_count}/{self.max_retries}...")

                    # 触发轮询更新回调
                    if self.on_polling_update:
                        self.on_polling_update(
                            f"正在尝试第{retry_count}次激活确认...",
                            retry_count
                        )

                    # 发送激活请求
                    async with session.post(
                        self.activation_url,
                        headers=self.request_headers,
                        json=payload
                    ) as response:
                        response_text = await response.text()

                        # 记录响应
                        logger.debug(f"HTTP状态码: {response.status}")
                        try:
                            response_json = json.loads(response_text)
                            logger.debug(f"响应内容: {json.dumps(response_json, indent=2)}")
                        except json.JSONDecodeError:
                            logger.debug(f"响应内容(非JSON): {response_text}")

                        # 处理不同的响应状态码
                        if response.status == 200:
                            # 激活成功
                            logger.info("✅ 设备激活成功!")

                            try:
                                response_data = json.loads(response_text)
                            except json.JSONDecodeError:
                                response_data = {}

                            # 提取激活信息
                            websocket_url = response_data.get("websocket_url", "")
                            access_token = response_data.get("access_token", "")

                            result = BindStatusResult(
                                success=True,
                                is_activated=True,
                                websocket_url=websocket_url,
                                access_token=access_token,
                                message="设备绑定确认成功",
                                activation_data=response_data
                            )

                            # 触发成功回调
                            if self.on_bind_confirmed:
                                self.on_bind_confirmed(result)

                            return result

                        elif response.status == 202:
                            # 等待用户输入验证码
                            logger.info("⏳ 等待用户输入验证码...")
                            last_error = "等待验证码输入"

                        else:
                            # 其他错误状态
                            error_msg = "未知错误"
                            try:
                                error_data = json.loads(response_text)
                                error_msg = error_data.get("error", f"HTTP {response.status}")
                            except json.JSONDecodeError:
                                error_msg = f"HTTP {response.status}: {response_text[:100]}"

                            logger.warning(f"服务器响应错误: {error_msg}")
                            last_error = error_msg

                            # 特殊错误处理
                            if "Device not found" in error_msg and retry_count % 5 == 0:
                                logger.warning("💡 提示: 如果错误持续出现，请尝试重新获取验证码")

                except asyncio.TimeoutError:
                    error_msg = "请求超时"
                    logger.warning(f"⏰ {error_msg}")
                    last_error = error_msg

                except aiohttp.ClientError as e:
                    error_msg = f"网络请求失败: {str(e)}"
                    logger.warning(f"🌐 {error_msg}")
                    last_error = error_msg

                except Exception as e:
                    error_msg = f"未知异常: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    last_error = error_msg

                # 等待下一次轮询（如果还有重试次数）
                if retry_count < self.max_retries:
                    logger.debug(f"等待 {self.retry_interval} 秒后重试...")
                    await asyncio.sleep(self.retry_interval)

        # 轮询失败
        final_error = last_error or "达到最大重试次数"
        logger.error(f"❌ 绑定确认失败: {final_error}")

        # 触发错误回调
        if self.on_polling_error:
            self.on_polling_error(final_error)

        return BindStatusResult(
            success=False,
            message="绑定确认超时或失败",
            error_detail=final_error
        )

    def stop_polling(self):
        """停止轮询"""
        self.is_running = False
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
        logger.info("⏹️ 停止绑定状态轮询")


class BindStatusService:
    """绑定状态服务 - 管理轮询器的高级接口"""

    def __init__(self):
        """初始化绑定状态服务"""
        self.listener = BindStatusListener()
        self.current_result: Optional[BindStatusResult] = None
        self.status_callbacks = []

        # 设置监听器回调
        self.listener.on_bind_confirmed = self._on_bind_confirmed
        self.listener.on_polling_error = self._on_polling_error
        self.listener.on_polling_update = self._on_polling_update

    def add_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加状态回调"""
        self.status_callbacks.append(callback)

    def _on_bind_confirmed(self, result: BindStatusResult):
        """绑定确认回调"""
        self.current_result = result
        self._notify_status("bind_success", {
            "websocket_url": result.websocket_url,
            "access_token": result.access_token,
            "message": result.message
        })

    def _on_polling_error(self, error_message: str):
        """轮询错误回调"""
        self._notify_status("polling_error", {
            "error": error_message,
            "retry_available": True
        })

    def _on_polling_update(self, message: str, retry_count: int):
        """轮询更新回调"""
        self._notify_status("polling_update", {
            "message": message,
            "retry_count": retry_count,
            "max_retries": self.listener.max_retries
        })

    def _notify_status(self, status: str, data: Dict[str, Any]):
        """通知状态变化"""
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                logger.error(f"状态回调执行失败: {e}")

    async def wait_for_binding_confirmation(
        self,
        challenge: str,
        timeout: int = 300
    ) -> BindStatusResult:
        """
        等待绑定确认

        Args:
            challenge: 服务器挑战字符串
            timeout: 超时时间

        Returns:
            BindStatusResult: 绑定结果
        """
        logger.info("🔄 开始等待设备绑定确认...")
        result = await self.listener.start_polling(challenge, timeout)
        self.current_result = result
        return result

    def get_current_status(self) -> Optional[BindStatusResult]:
        """获取当前绑定状态"""
        return self.current_result

    def is_polling(self) -> bool:
        """检查是否正在轮询"""
        return self.listener.is_running

    def stop(self):
        """停止服务"""
        self.listener.stop_polling()


# 全局绑定状态服务实例
_bind_status_service_instance: Optional[BindStatusService] = None


def get_bind_status_service() -> BindStatusService:
    """获取绑定状态服务实例（单例）"""
    global _bind_status_service_instance
    if _bind_status_service_instance is None:
        _bind_status_service_instance = BindStatusService()
    return _bind_status_service_instance


async def wait_for_device_binding(challenge: str, timeout: int = 300) -> BindStatusResult:
    """
    等待设备绑定确认的便捷函数

    Args:
        challenge: 服务器挑战字符串
        timeout: 超时时间

    Returns:
        BindStatusResult: 绑定结果
    """
    service = get_bind_status_service()
    return await service.wait_for_binding_confirmation(challenge, timeout)


if __name__ == "__main__":
    # 测试轮询功能
    async def test_polling():
        # 模拟挑战字符串
        test_challenge = "test-challenge-123"

        result = await wait_for_device_binding(test_challenge, timeout=30)
        print(f"轮询结果: {result}")

    asyncio.run(test_polling())