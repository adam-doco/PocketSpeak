"""
PocketSpeak 设备激活客户端 - 完全复刻py-xiaozhi激活请求逻辑
严格按照py-xiaozhi的HTTP请求格式和激活流程实现
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from services.device_lifecycle import pocketspeak_device_manager


class PocketSpeakActivator:
    """完全复刻py-xiaozhi的设备激活逻辑"""

    def __init__(self, activate_url: str = "https://api.tenclass.net/xiaozhi/activate/"):
        self.activate_url = activate_url
        if not self.activate_url.endswith("/"):
            self.activate_url += "/"

    async def request_activation_code(self) -> Dict[str, Any]:
        """请求激活验证码 - 完全复刻py-xiaozhi的激活请求流程"""

        # 1. 检查设备是否已激活
        if pocketspeak_device_manager.check_activation_status():
            return {
                "success": False,
                "message": "设备已激活，无需重复激活",
                "verification_code": None,
                "is_already_activated": True
            }

        # 2. 确保设备身份信息存在
        serial_number, hmac_key, _ = pocketspeak_device_manager.ensure_device_identity()

        if not serial_number or not hmac_key:
            return {
                "success": False,
                "message": "设备身份信息创建失败",
                "error": "无法生成序列号或HMAC密钥"
            }

        # 3. 获取设备信息用于请求
        device_id = pocketspeak_device_manager.get_device_id()
        client_id = pocketspeak_device_manager.get_client_id()

        # 4. 构造请求头 - 完全按照py-xiaozhi格式
        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
            "Activation-Version": "2",
            "Content-Type": "application/json",
            "User-Agent": "PocketSpeak/1.0"
        }

        # 5. 构造请求体 - 使用py-xiaozhi的激活格式而非OTA格式
        request_body = {
            "Payload": {
                "algorithm": "hmac-sha256",
                "serial_number": serial_number
                # 注意：不包含challenge和hmac，这是初始请求获取验证码
            }
        }

        print(f"🌐 发送激活请求: {self.activate_url}")
        print(f"📱 设备ID: {device_id}")
        print(f"🆔 客户端ID: {client_id}")
        print(f"🏷️ 序列号: {serial_number}")
        print(f"📋 请求头: {headers}")
        print(f"📦 请求体: {request_body}")

        try:
            # 6. 发送HTTP POST请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.activate_url,
                    headers=headers,
                    json=request_body
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    print(f"📡 响应状态: HTTP {status_code}")
                    print(f"📄 响应内容: {response_text}")

                    if status_code == 200:
                        try:
                            response_data = await response.json()

                            # 7. 解析响应获取验证码
                            challenge = response_data.get("challenge")
                            code = response_data.get("code")
                            message = response_data.get("message", "请在xiaozhi.me输入验证码")

                            if challenge and code:
                                return {
                                    "success": True,
                                    "verification_code": code,
                                    "challenge": challenge,
                                    "message": message,
                                    "serial_number": serial_number,
                                    "device_id": device_id,
                                    "server_response": response_data
                                }
                            else:
                                return {
                                    "success": False,
                                    "message": "服务器响应缺少验证码或挑战",
                                    "error": "invalid_response",
                                    "server_response": response_data
                                }

                        except Exception as e:
                            return {
                                "success": False,
                                "message": f"JSON解析失败: {e}",
                                "error": "json_parse_error",
                                "raw_response": response_text
                            }
                    else:
                        return {
                            "success": False,
                            "message": f"HTTP {status_code} 错误",
                            "error": f"http_error_{status_code}",
                            "raw_response": response_text
                        }

        except Exception as e:
            return {
                "success": False,
                "message": f"请求失败: {str(e)}",
                "error": "network_error"
            }

    async def confirm_activation(self, challenge: str) -> Dict[str, Any]:
        """确认激活 - 通过HMAC签名验证激活状态"""

        # 1. 获取设备信息
        serial_number = pocketspeak_device_manager.get_serial_number()
        device_id = pocketspeak_device_manager.get_device_id()
        client_id = pocketspeak_device_manager.get_client_id()

        if not all([serial_number, device_id, client_id]):
            return {
                "success": False,
                "message": "设备信息不完整"
            }

        # 2. 生成HMAC签名
        hmac_signature = pocketspeak_device_manager.generate_hmac_signature(challenge)
        if not hmac_signature:
            return {
                "success": False,
                "message": "HMAC签名生成失败"
            }

        # 3. 构造确认请求
        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
            "Activation-Version": "2",
            "Content-Type": "application/json",
            "User-Agent": "PocketSpeak/1.0"
        }

        request_body = {
            "Payload": {
                "algorithm": "hmac-sha256",
                "serial_number": serial_number,
                "challenge": challenge,
                "hmac": hmac_signature
            }
        }

        print(f"🔐 发送激活确认请求")
        print(f"🏷️ 序列号: {serial_number}")
        print(f"🎯 挑战: {challenge}")
        print(f"🔑 HMAC签名: {hmac_signature}")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.activate_url,
                    headers=headers,
                    json=request_body
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    print(f"📡 确认响应状态: HTTP {status_code}")
                    print(f"📄 确认响应内容: {response_text}")

                    if status_code == 200:
                        try:
                            response_data = await response.json()

                            # 检查激活是否成功
                            if response_data.get("success") or response_data.get("activated"):
                                # 标记设备为已激活
                                pocketspeak_device_manager.mark_device_as_activated()

                                return {
                                    "success": True,
                                    "message": "设备激活成功",
                                    "is_activated": True,
                                    "server_response": response_data
                                }
                            else:
                                return {
                                    "success": False,
                                    "message": "服务器未确认激活",
                                    "server_response": response_data
                                }

                        except Exception as e:
                            return {
                                "success": False,
                                "message": f"JSON解析失败: {e}",
                                "raw_response": response_text
                            }
                    else:
                        return {
                            "success": False,
                            "message": f"HTTP {status_code} 错误",
                            "raw_response": response_text
                        }

        except Exception as e:
            return {
                "success": False,
                "message": f"确认请求失败: {str(e)}"
            }

    async def get_activation_status(self) -> Dict[str, Any]:
        """
        获取激活状态 - 真正轮询小智AI服务器
        这个方法会向小智AI服务器查询设备是否已被用户激活
        """
        try:
            # 1. 首先检查本地激活状态
            local_is_activated = pocketspeak_device_manager.check_activation_status()
            device_info = pocketspeak_device_manager.get_device_info()

            if local_is_activated:
                return {
                    "is_activated": True,
                    "device_id": device_info.get("device_id"),
                    "serial_number": device_info.get("serial_number"),
                    "activation_status": "已激活",
                    "websocket_url": "wss://api.xiaozhi.com/v1/ws",
                    "access_token": "pocketspeak_activated"
                }

            # 2. 如果本地未激活，向小智AI服务器查询激活状态
            serial_number = device_info.get("serial_number")
            device_id = device_info.get("device_id")
            client_id = device_info.get("client_id")

            if not serial_number or not device_id:
                return {
                    "is_activated": False,
                    "device_id": device_id,
                    "serial_number": serial_number,
                    "activation_status": "设备信息不完整",
                    "error": "缺少设备序列号或ID"
                }

            # 3. 构造轮询请求 - 查询设备激活状态
            headers = {
                "DeviceId": device_id,
                "ClientId": client_id,
                "Activation-Version": "2",
                "Content-Type": "application/json",
                "User-Agent": "PocketSpeak/1.0"
            }

            # 构造状态查询请求体
            request_body = {
                "Payload": {
                    "action": "check_activation",
                    "serial_number": serial_number,
                    "device_id": device_id
                }
            }

            print(f"🔍 轮询小智AI服务器激活状态...")
            print(f"📱 设备ID: {device_id}")
            print(f"🏷️ 序列号: {serial_number}")

            # 4. 发送状态查询请求
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.activate_url,  # 使用相同的激活URL进行状态查询
                    headers=headers,
                    json=request_body
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    print(f"📡 轮询响应状态: HTTP {status_code}")
                    print(f"📄 轮询响应内容: {response_text}")

                    if status_code == 200:
                        try:
                            response_data = await response.json()

                            # 检查服务器返回的激活状态
                            server_activated = response_data.get("activated", False)
                            activation_info = response_data.get("activation_info", {})

                            if server_activated:
                                # 服务器确认设备已激活，同步到本地
                                print("✅ 服务器确认设备已激活，更新本地状态...")
                                pocketspeak_device_manager.mark_device_as_activated()

                                return {
                                    "is_activated": True,
                                    "device_id": device_id,
                                    "serial_number": serial_number,
                                    "activation_status": "服务器确认已激活",
                                    "websocket_url": activation_info.get("websocket_url", "wss://api.xiaozhi.com/v1/ws"),
                                    "access_token": activation_info.get("access_token", "pocketspeak_activated"),
                                    "server_response": response_data
                                }
                            else:
                                # 服务器确认设备未激活
                                return {
                                    "is_activated": False,
                                    "device_id": device_id,
                                    "serial_number": serial_number,
                                    "activation_status": "等待用户在xiaozhi.me完成激活",
                                    "message": "请在xiaozhi.me输入验证码完成设备激活"
                                }

                        except Exception as e:
                            print(f"❌ 解析服务器响应失败: {e}")
                            # JSON解析失败，返回本地状态
                            return {
                                "is_activated": False,
                                "device_id": device_id,
                                "serial_number": serial_number,
                                "activation_status": "服务器响应解析失败",
                                "error": str(e)
                            }
                    else:
                        print(f"⚠️ 服务器轮询失败: HTTP {status_code}")
                        # 服务器请求失败，返回本地状态
                        return {
                            "is_activated": False,
                            "device_id": device_id,
                            "serial_number": serial_number,
                            "activation_status": f"服务器轮询失败 (HTTP {status_code})",
                            "error": f"HTTP {status_code}: {response_text}"
                        }

        except Exception as e:
            print(f"❌ 轮询激活状态发生错误: {e}")
            # 网络错误等，返回本地状态
            device_info = pocketspeak_device_manager.get_device_info()
            return {
                "is_activated": False,
                "device_id": device_info.get("device_id"),
                "serial_number": device_info.get("serial_number"),
                "activation_status": "轮询网络错误",
                "error": str(e)
            }

    def manual_mark_activated(self) -> bool:
        """手动标记设备为已激活（用于用户在官网完成绑定后）"""
        return pocketspeak_device_manager.mark_device_as_activated()


# 全局实例
pocketspeak_activator = PocketSpeakActivator()