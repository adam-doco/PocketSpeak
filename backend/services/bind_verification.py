"""
PocketSpeak 验证码绑定模块
负责与小智AI服务器建立HTTP连接并获取验证码

基于 py-xiaozhi 项目的 device_activator.py 实现，使用HTTP API替代WebSocket
参考路径:
- backend/libs/py_xiaozhi/src/utils/device_activator.py
"""

import asyncio
import json
import aiohttp
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import time

from core.device_manager import device_manager
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class BindingResult:
    """绑定结果数据类"""
    success: bool
    verification_code: Optional[str] = None
    message: str = ""
    challenge: Optional[str] = None
    websocket_url: Optional[str] = None
    access_token: Optional[str] = None
    error_detail: Optional[str] = None


class XiaoZhiHTTPClient:
    """小智AI HTTP客户端 - 专门用于设备绑定流程"""

    def __init__(self):
        """初始化HTTP客户端"""
        self.connected = False
        self._is_closing = False

        # 消息回调
        self.on_verification_code: Optional[Callable[[str, str, str], None]] = None
        self.on_bind_success: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_network_error: Optional[Callable[[str], None]] = None

        # 使用正确的OTA URL构建activate接口
        ota_base_url = settings.xiaozhi_ota_url
        if not ota_base_url.endswith("/"):
            ota_base_url += "/"
        self.activate_url = f"{ota_base_url}activate"

        # ✅ 正确实现：按照py-xiaozhi的config_manager逻辑
        # Device-Id = MAC地址, Client-Id = UUID
        import uuid

        mac_address = device_manager.get_mac_address()
        client_id = str(uuid.uuid4())

        self.headers = {
            "Activation-Version": "2",
            "Device-Id": mac_address,  # 使用MAC地址作为Device-Id
            "Client-Id": client_id,    # 生成UUID作为Client-Id
            "Content-Type": "application/json",
        }

        logger.info(f"✅ 正确的Device-Id: {mac_address}")
        logger.info(f"✅ 生成的Client-Id: {client_id}")

        logger.info(f"初始化小智HTTP客户端: {self.activate_url}")

    async def start_activation(self) -> Dict[str, Any]:
        """启动设备激活流程，获取challenge和验证码"""
        try:
            logger.info(f"正在连接到小智AI服务器: {self.activate_url}")

            # 获取设备信息和生成HMAC payload
            serial_number, hmac_key, is_activated = device_manager.ensure_device_identity()

            if not serial_number or not hmac_key:
                raise Exception("设备身份信息不完整")

            # 生成初始challenge - 根据py-xiaozhi源码，初始请求使用设备序列号作为challenge
            initial_challenge = serial_number
            # 对于初始激活请求，使用序列号作为challenge生成HMAC
            hmac_signature = device_manager._device_fingerprint.generate_hmac(initial_challenge)

            # 构建payload
            payload = {
                "Payload": {
                    "algorithm": "hmac-sha256",
                    "serial_number": serial_number,
                    "challenge": initial_challenge,
                    "hmac": hmac_signature,
                }
            }

            logger.info(f"请求头: {self.headers}")
            logger.info(f"请求负载: {json.dumps(payload, indent=2)}")
            logger.info(f"MAC地址信息: {device_manager.get_mac_address()}")
            logger.info(f"设备指纹详情: {device_manager._device_fingerprint.generate_fingerprint()}")

            # 发送HTTP请求获取激活信息
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.activate_url,
                    headers=self.headers,
                    json=payload
                ) as response:

                    response_text = await response.text()
                    logger.info(f"激活响应 (HTTP {response.status}): {response_text[:200]}...")

                    if response.status == 200:
                        # 已经激活
                        logger.info("设备已激活")
                        return {
                            "success": True,
                            "verification_code": None,
                            "message": "设备已激活",
                            "challenge": None,
                            "is_activated": True
                        }

                    elif response.status == 202:
                        # 需要用户激活，解析响应获取验证码和challenge
                        try:
                            response_data = json.loads(response_text)

                            # 从响应中提取激活信息
                            server_challenge = response_data.get("challenge", "")
                            # 如果服务器没有返回challenge或返回空字符串，使用初始challenge
                            challenge = server_challenge if server_challenge else initial_challenge
                            verification_code = response_data.get("code", "000000")
                            message = response_data.get("message", "请在xiaozhi.me输入验证码")

                            logger.info(f"服务器challenge: '{server_challenge}', 使用challenge: '{challenge}'")

                            logger.info(f"获取到验证码: {verification_code}")
                            logger.info(f"激活提示: {message}")

                            if self.on_verification_code:
                                self.on_verification_code(verification_code, challenge, message)

                            return {
                                "success": True,
                                "verification_code": verification_code,
                                "message": message,
                                "challenge": challenge,
                                "is_activated": False
                            }

                        except json.JSONDecodeError:
                            logger.error("无法解析激活响应")
                            return {
                                "success": False,
                                "verification_code": None,
                                "message": "响应格式错误",
                                "challenge": None
                            }

                    else:
                        # 其他错误状态
                        error_msg = f"服务器返回错误状态: {response.status}"
                        try:
                            error_data = json.loads(response_text)
                            error_msg = error_data.get("error", error_msg)
                        except json.JSONDecodeError:
                            pass

                        logger.error(error_msg)
                        if self.on_network_error:
                            self.on_network_error(error_msg)

                        return {
                            "success": False,
                            "verification_code": None,
                            "message": error_msg,
                            "challenge": None
                        }

        except Exception as e:
            import traceback
            logger.error(f"启动激活流程失败: {e}")
            logger.error(f"完整错误信息: {traceback.format_exc()}")
            if self.on_network_error:
                self.on_network_error(f"连接失败: {str(e)}")

            return {
                "success": False,
                "verification_code": None,
                "message": f"网络错误: {str(e)}",
                "challenge": None
            }

    async def poll_activation_status(self, challenge: str, code: str = None) -> Dict[str, Any]:
        """轮询激活状态，等待用户完成验证码输入 - 基于device_activator.py实现"""
        try:
            # 检查challenge字段是否有效 - 按照device_activator.py的要求
            if not challenge:
                raise Exception("挑战字符串不能为空")

            logger.info(f"开始轮询激活状态 - Challenge: {challenge}, Code: {code}")

            # 获取设备信息和生成HMAC payload
            serial_number, hmac_key, is_activated = device_manager.ensure_device_identity()

            if not serial_number or not hmac_key:
                raise Exception("设备身份信息不完整")

            # 计算HMAC签名
            hmac_signature = device_manager._device_fingerprint.generate_hmac(challenge)

            # 构建payload - 与device_activator.py保持一致
            payload = {
                "Payload": {
                    "algorithm": "hmac-sha256",
                    "serial_number": serial_number,
                    "challenge": challenge,
                    "hmac": hmac_signature,
                }
            }

            logger.debug(f"轮询激活状态 - Challenge: {challenge}")
            logger.debug(f"轮询负载: {json.dumps(payload, indent=2)}")

            # 长轮询机制 - 基于device_activator.py的实现
            max_retries = 60  # 最长等待5分钟
            retry_interval = 5  # 5秒重试间隔

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for attempt in range(max_retries):
                    try:
                        logger.info(f"轮询激活状态 (尝试 {attempt + 1}/{max_retries})...")

                        # 每隔几次重试时重新播放验证码提示
                        if attempt > 0 and attempt % 10 == 0 and code:
                            logger.info(f"提醒: 请在xiaozhi.me输入验证码: {code}")

                        async with session.post(
                            self.activate_url,
                            headers=self.headers,
                            json=payload
                        ) as response:
                            response_text = await response.text()

                            if response.status == 200:
                                # 激活成功！
                                try:
                                    response_data = json.loads(response_text)
                                    logger.info("🎉 设备激活成功!")
                                    logger.info(f"激活响应: {json.dumps(response_data, indent=2)}")

                                    # 设置激活状态
                                    device_manager._device_fingerprint.set_activation_status(True)

                                    # 触发绑定成功回调
                                    if self.on_bind_success:
                                        websocket_url = response_data.get("websocket", {}).get("url", "")
                                        access_token = response_data.get("websocket", {}).get("token", "")
                                        self.on_bind_success({
                                            "websocket_url": websocket_url,
                                            "access_token": access_token,
                                            "bind_data": response_data
                                        })

                                    return {
                                        "success": True,
                                        "verification_code": code,
                                        "message": "设备激活成功",
                                        "challenge": challenge,
                                        "websocket_url": response_data.get("websocket", {}).get("url"),
                                        "access_token": response_data.get("websocket", {}).get("token"),
                                        "is_activated": True
                                    }

                                except json.JSONDecodeError:
                                    logger.error("激活成功但响应格式错误")
                                    return {
                                        "success": True,
                                        "verification_code": code,
                                        "message": "设备激活成功",
                                        "challenge": challenge,
                                        "is_activated": True
                                    }

                            elif response.status == 202:
                                # 继续等待用户输入验证码
                                logger.debug("等待用户输入验证码...")
                                await asyncio.sleep(retry_interval)
                                continue

                            else:
                                # 处理错误但继续重试
                                error_msg = f"服务器返回错误状态: {response.status}"
                                try:
                                    error_data = json.loads(response_text)
                                    error_msg = error_data.get("error", error_msg)
                                except json.JSONDecodeError:
                                    pass

                                logger.warning(f"服务器响应: {error_msg}，继续等待...")
                                await asyncio.sleep(retry_interval)
                                continue

                    except asyncio.CancelledError:
                        logger.info("轮询被取消")
                        return {
                            "success": False,
                            "verification_code": code,
                            "message": "轮询被取消",
                            "challenge": challenge
                        }

                    except Exception as e:
                        logger.warning(f"轮询过程中发生错误: {e}，继续重试...")
                        await asyncio.sleep(retry_interval)
                        continue

                # 达到最大重试次数
                logger.error(f"激活超时，达到最大重试次数 ({max_retries})")
                return {
                    "success": False,
                    "verification_code": code,
                    "message": "等待激活超时",
                    "challenge": challenge,
                    "error_detail": f"在{max_retries * retry_interval}秒内未完成激活"
                }

        except Exception as e:
            logger.error(f"轮询激活状态失败: {e}")
            return {
                "success": False,
                "verification_code": code,
                "message": f"轮询错误: {str(e)}",
                "challenge": challenge
            }

    async def close(self):
        """关闭HTTP客户端"""
        self._is_closing = True
        self.connected = False
        logger.debug("HTTP客户端已关闭")



class BindVerificationService:
    """验证码绑定服务 - PocketSpeak设备绑定管理器"""

    def __init__(self):
        """初始化绑定服务"""
        self.client = XiaoZhiHTTPClient()
        self.current_verification_code: Optional[str] = None
        self.current_challenge: Optional[str] = None
        self.bind_result: Optional[BindingResult] = None
        self.verification_received_event = asyncio.Event()
        self.bind_success_event = asyncio.Event()

        # 设置客户端回调
        self.client.on_verification_code = self._on_verification_code
        self.client.on_bind_success = self._on_bind_success
        self.client.on_network_error = self._on_network_error

        logger.info("初始化验证码绑定服务")

    def _on_verification_code(self, code: str, challenge: str, message: str):
        """验证码回调处理"""
        self.current_verification_code = code
        self.current_challenge = challenge

        logger.info("="*60)
        logger.info("🔐 PocketSpeak 设备绑定验证码")
        logger.info("="*60)
        logger.info(f"📱 验证码: {code}")
        logger.info(f"💡 请前往 xiaozhi.me 输入此验证码完成设备绑定")
        logger.info(f"📋 提示: {message}")
        logger.info("="*60)

        # 触发验证码接收事件
        self.verification_received_event.set()

    def _on_bind_success(self, bind_data: Dict[str, Any]):
        """绑定成功回调处理"""
        self.bind_result = BindingResult(
            success=True,
            verification_code=self.current_verification_code,
            message="设备绑定成功",
            websocket_url=bind_data.get("websocket_url"),
            access_token=bind_data.get("access_token"),
        )

        logger.info("🎉 设备绑定成功!")
        logger.info(f"🔗 WebSocket URL: {bind_data.get('websocket_url', 'N/A')}")

        # 触发绑定成功事件
        self.bind_success_event.set()

    def _on_network_error(self, error_message: str):
        """网络错误回调处理"""
        logger.error(f"❌ 网络错误: {error_message}")

        self.bind_result = BindingResult(
            success=False,
            message="网络连接错误",
            error_detail=error_message,
        )

    async def start_binding_process(self, timeout: int = 300) -> BindingResult:
        """
        启动设备绑定流程

        Args:
            timeout: 超时时间(秒)，默认5分钟

        Returns:
            BindingResult: 绑定结果
        """
        try:
            logger.info("🚀 启动PocketSpeak设备绑定流程...")

            # 重置状态
            self.verification_received_event.clear()
            self.bind_success_event.clear()
            self.bind_result = None

            # 第一步：启动激活流程，获取验证码和challenge
            logger.info("📡 启动设备激活流程...")
            activation_result = await self.client.start_activation()

            if not activation_result["success"]:
                return BindingResult(
                    success=False,
                    message=activation_result["message"],
                    error_detail=activation_result.get("error_detail")
                )

            # 如果设备已激活，直接返回成功
            if activation_result.get("is_activated"):
                return BindingResult(
                    success=True,
                    message="设备已激活",
                    verification_code=None,
                    challenge=None
                )

            # 获取验证码和challenge
            verification_code = activation_result["verification_code"]
            challenge = activation_result["challenge"]
            message = activation_result["message"]

            # 保存当前状态
            self.current_verification_code = verification_code
            self.current_challenge = challenge

            # 显示验证码信息
            self._on_verification_code(verification_code, challenge, message)

            logger.info("✅ 验证码已显示，请前往xiaozhi.me完成绑定")

            # 第二步：开始轮询激活状态
            logger.info("⏳ 开始轮询激活状态...")
            polling_result = await self.client.poll_activation_status(challenge, verification_code)

            if polling_result["success"]:
                # 激活成功，构建绑定结果
                self.bind_result = BindingResult(
                    success=True,
                    verification_code=verification_code,
                    message="设备激活成功",
                    challenge=challenge,
                    websocket_url=polling_result.get("websocket_url"),
                    access_token=polling_result.get("access_token")
                )
                return self.bind_result
            else:
                # 激活失败
                return BindingResult(
                    success=False,
                    verification_code=verification_code,
                    message=polling_result["message"],
                    challenge=challenge,
                    error_detail=polling_result.get("error_detail")
                )

        except Exception as e:
            logger.error(f"绑定流程异常: {e}")
            await self.client.close()
            return BindingResult(
                success=False,
                message="绑定流程发生异常",
                error_detail=str(e)
            )

    async def get_current_verification_code(self) -> Optional[str]:
        """获取当前验证码"""
        return self.current_verification_code

    async def close(self):
        """关闭绑定服务"""
        await self.client.close()


# 全局绑定服务实例
_bind_service_instance: Optional[BindVerificationService] = None


def get_bind_verification_service() -> BindVerificationService:
    """获取验证码绑定服务实例（单例）"""
    global _bind_service_instance
    if _bind_service_instance is None:
        _bind_service_instance = BindVerificationService()
    return _bind_service_instance


async def start_device_binding(timeout: int = 300) -> BindingResult:
    """
    启动设备绑定流程的便捷函数

    Args:
        timeout: 超时时间(秒)

    Returns:
        BindingResult: 绑定结果
    """
    service = get_bind_verification_service()
    return await service.start_binding_process(timeout)


if __name__ == "__main__":
    # 测试绑定流程
    async def test_binding():
        result = await start_device_binding()
        print(f"绑定结果: {result}")

    asyncio.run(test_binding())