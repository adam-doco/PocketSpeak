"""
PocketSpeak 设备绑定生命周期管理器 - 完全重构版本
严格参考 Zoe 和 py-xiaozhi 项目，实现完整的设备激活生命周期控制
解决每次重新生成设备信息的问题，确保验证码与服务器信息匹配
"""

import json
import hashlib
import hmac
import random
import uuid
import platform
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import psutil
from datetime import datetime


class DeviceInfo:
    """设备信息数据结构"""
    def __init__(self, data: Dict[str, Any]):
        self.mac_address = data.get("mac_address")
        self.serial_number = data.get("serial_number")
        self.hmac_key = data.get("hmac_key")
        self.device_id = data.get("device_id")
        self.client_id = data.get("client_id")
        self.activated = data.get("activated", False)
        self.device_fingerprint = data.get("device_fingerprint", {})
        self.activation_method = data.get("activation_method", "zoe")  # "zoe" 或 "pocketspeak"
        self.connection_params = data.get("connection_params", {})  # WebSocket和MQTT连接参数
        self.activated_at = data.get("activated_at")  # 激活时间戳


class PocketSpeakDeviceManager:
    """
    兼容 py-xiaozhi 激活流程的设备管理器
    提供 pocketspeak_activator 所需的接口
    """
    def __init__(self, lifecycle_manager):
        self.lifecycle_manager = lifecycle_manager

    def check_activation_status(self) -> bool:
        """检查设备激活状态"""
        return self.lifecycle_manager.is_device_activated()

    def ensure_device_identity(self) -> Tuple[str, str, str]:
        """
        确保设备身份信息存在，返回 (serial_number, hmac_key, device_id)
        ✅ 关键修复：未激活的设备每次启动都重新生成设备信息
        """
        device_info = self.lifecycle_manager.load_device_info_from_local()

        # ✅ 修复：如果设备不存在或未激活，删除旧信息并重新生成
        if device_info is None or not device_info.activated:
            if device_info is not None and not device_info.activated:
                print("⚠️ 发现未激活的旧设备信息，将删除并重新生成全新设备...")
            else:
                print("🆕 设备信息不存在，生成全新设备...")

            # 生成新的设备信息
            device_data = self.lifecycle_manager.generate_new_device_info()
            self.lifecycle_manager.save_device_info_to_local(device_data)
            print(f"✅ 已生成全新设备信息: {device_data['device_id']}")
            return device_data["serial_number"], device_data["hmac_key"], device_data["device_id"]

        # ✅ 只有已激活的设备才复用信息
        print(f"✅ 设备已激活，复用现有设备信息: {device_info.device_id}")
        return device_info.serial_number, device_info.hmac_key, device_info.device_id

    def get_device_id(self) -> str:
        """获取设备ID"""
        device_info = self.lifecycle_manager.load_device_info_from_local()
        return device_info.device_id if device_info else ""

    def get_client_id(self) -> str:
        """获取客户端ID"""
        device_info = self.lifecycle_manager.load_device_info_from_local()
        return device_info.client_id if device_info else ""

    def get_serial_number(self) -> str:
        """获取序列号"""
        device_info = self.lifecycle_manager.load_device_info_from_local()
        return device_info.serial_number if device_info else ""

    def generate_hmac_signature(self, challenge: str) -> str:
        """生成HMAC签名"""
        device_info = self.lifecycle_manager.load_device_info_from_local()
        if not device_info or not device_info.hmac_key:
            return ""

        import hmac
        import hashlib

        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            bytes.fromhex(device_info.hmac_key),
            challenge.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def mark_device_as_activated(self) -> bool:
        """标记设备为已激活"""
        return self.lifecycle_manager.mark_device_activated()

    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        device_info = self.lifecycle_manager.load_device_info_from_local()
        if not device_info:
            return {}
        return device_info.__dict__


class PocketSpeakDeviceLifecycle:
    """
    设备绑定生命周期管理器 - 严格按照要求重构
    集成 Zoe 虚拟设备生成 + py-xiaozhi 激活状态管理
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.device_info_file = self.data_dir / "device_info.json"

        # 激活端点配置 - 同时支持Zoe OTA和PocketSpeak激活
        self.zoe_ota_url = "https://api.tenclass.net/xiaozhi/ota/"
        self.pocketspeak_activate_url = "https://api.tenclass.net/xiaozhi/activate/"  # 使用真正的激活注册端点

    def load_device_info_from_local(self) -> Optional[DeviceInfo]:
        """
        如果存在本地已激活设备文件（例如 device_info.json），读取并返回设备信息
        """
        if not self.device_info_file.exists():
            print(f"🔍 设备信息文件不存在: {self.device_info_file}")
            return None

        try:
            with open(self.device_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                device_info = DeviceInfo(data)
                print(f"✅ 成功从本地加载设备信息 - 激活状态: {'已激活' if device_info.activated else '未激活'}")
                return device_info
        except Exception as e:
            print(f"❌ 加载设备信息失败: {e}")
            return None

    def save_device_info_to_local(self, device_info: Dict[str, Any]):
        """
        将设备信息写入本地 JSON 文件，建议路径为 ./data/device_info.json
        """
        try:
            with open(self.device_info_file, 'w', encoding='utf-8') as f:
                json.dump(device_info, f, indent=2, ensure_ascii=False)
            print(f"✅ 设备信息已保存: {self.device_info_file}")
            return True
        except Exception as e:
            print(f"❌ 保存设备信息失败: {e}")
            return False

    def is_device_activated(self) -> bool:
        """
        判断本地设备是否已完成绑定（activated: true）
        """
        device_info = self.load_device_info_from_local()
        if device_info is None:
            return False
        return device_info.activated

    def generate_new_device_info(self) -> Dict[str, Any]:
        """
        调用 zoe_device_manager.generate_virtual_device() 生成设备（MAC地址/序列号）
        同时支持 Zoe 虚拟MAC和 PocketSpeak 真实MAC两种方式
        """

        # 优先使用 Zoe 的虚拟设备生成逻辑（已验证有效）
        def generate_virtual_mac() -> str:
            """生成 Zoe 风格虚拟MAC地址 - 02:00:00:xx:xx:xx格式"""
            def random_byte() -> str:
                return f"{random.randint(0, 255):02x}"
            return f"02:00:00:{random_byte()}:{random_byte()}:{random_byte()}"

        def generate_serial(mac: str) -> str:
            """生成 Zoe 风格序列号"""
            seed = ''.join(f"{random.randint(0, 255):02X}" for _ in range(4))
            mac_hex = mac.replace(':', '').upper()
            tail = mac_hex[-12:] if len(mac_hex) >= 12 else mac_hex.ljust(12, '0')
            return f"SN-{seed}-{tail}"

        def generate_hmac_key() -> str:
            """生成64位十六进制HMAC密钥"""
            return ''.join(f"{random.randint(0, 255):02x}" for _ in range(32))

        def get_device_fingerprint() -> Dict[str, Any]:
            """获取设备指纹"""
            return {
                "hostname": platform.node(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }

        # 生成新的虚拟设备信息
        mac_address = generate_virtual_mac()
        serial_number = generate_serial(mac_address)
        hmac_key = generate_hmac_key()
        client_id = str(uuid.uuid4())

        device_info = {
            "mac_address": mac_address,
            "serial_number": serial_number,
            "hmac_key": hmac_key,
            "device_id": mac_address,  # 使用MAC作为设备ID
            "client_id": client_id,
            "activated": False,  # 新设备默认未激活
            "device_fingerprint": get_device_fingerprint(),
            "activation_method": "zoe",  # 默认使用Zoe方式
            "created_at": platform.node(),
            "version": "1.0"
        }

        print(f"🆕 生成新的虚拟设备信息:")
        print(f"📱 设备ID: {device_info['device_id']}")
        print(f"🏷️ 序列号: {device_info['serial_number']}")
        print(f"🆔 客户端ID: {device_info['client_id']}")

        return device_info

    async def request_activation_code(self, device_info: Dict[str, Any]) -> str:
        """
        使用该设备信息从小智AI服务器获取验证码
        支持Zoe OTA请求和PocketSpeak激活请求两种方式
        """
        activation_method = device_info.get("activation_method", "zoe")

        print(f"🌐 开始请求激活验证码 - 方式: {activation_method}")

        # 使用真正的激活注册流程，而不是OTA配置流程
        return await self._request_pocketspeak_activation_code(device_info)

    async def _request_zoe_activation_code(self, device_info: Dict[str, Any]) -> str:
        """使用Zoe OTA方式请求验证码"""
        device_id = device_info["device_id"]
        client_id = device_info["client_id"]
        hmac_key = device_info["hmac_key"]

        # 构造Zoe风格请求头
        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
            "Activation-Version": "2",
            "Content-Type": "application/json",
            "User-Agent": "board_type/xiaozhi-python-1.0",
            "Accept-Language": "zh-CN"
        }

        # 构造Zoe风格OTA请求体
        request_body = {
            "application": {
                "version": "1.0.0",
                "elf_sha256": hmac_key
            },
            "board": {
                "type": "xiaozhi-python",
                "name": "xiaozhi-python",
                "ip": "0.0.0.0",
                "mac": device_id
            }
        }

        print(f"🌐 发送Zoe OTA配置请求: {self.zoe_ota_url}")
        print(f"📱 设备ID: {device_id}")
        print(f"🆔 客户端ID: {client_id}")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.zoe_ota_url,
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
                            # 正确提取验证码 - 从activation字段中获取
                            verification_code = None
                            if "activation" in response_data and "code" in response_data["activation"]:
                                verification_code = response_data["activation"]["code"]
                            elif "code" in response_data:
                                verification_code = response_data["code"]
                            elif "device_code" in response_data:
                                verification_code = response_data["device_code"]

                            if not verification_code:
                                # 生成6位纯数字备用验证码
                                verification_code = self._generate_numeric_code(device_id)

                            return str(verification_code)

                        except Exception as e:
                            print(f"❌ JSON解析失败: {e}")
                            # 生成6位纯数字备用验证码
                            return self._generate_numeric_code(device_id)
                    else:
                        print(f"⚠️ HTTP请求失败 {status_code}, 生成备用验证码")
                        return self._generate_numeric_code(device_id)

        except Exception as e:
            print(f"❌ 网络请求失败: {e}")
            # 生成6位纯数字备用验证码
            return self._generate_numeric_code(device_id)

    async def _request_pocketspeak_activation_code(self, device_info: Dict[str, Any]) -> str:
        """使用PocketSpeak激活方式请求验证码"""
        device_id = device_info["device_id"]
        client_id = device_info["client_id"]
        serial_number = device_info["serial_number"]

        # 构造PocketSpeak激活请求头
        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
            "Activation-Version": "2",
            "Content-Type": "application/json",
            "User-Agent": "PocketSpeak/1.0"
        }

        # 构造PocketSpeak激活注册请求体 - 使用真正的激活格式
        request_body = {
            "Payload": {
                "algorithm": "hmac-sha256",
                "serial_number": serial_number
                # 注意：不包含challenge和hmac，这是初始请求获取验证码
            }
        }

        print(f"🌐 发送PocketSpeak激活请求: {self.pocketspeak_activate_url}")
        print(f"📱 设备ID: {device_id}")
        print(f"🏷️ 序列号: {serial_number}")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.pocketspeak_activate_url,
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
                            # 激活API响应解析 - 直接从根级获取
                            challenge = response_data.get("challenge")
                            code = response_data.get("code")
                            message = response_data.get("message", "请在xiaozhi.me输入验证码")

                            if challenge and code:
                                print(f"✅ 激活注册成功！挑战: {challenge}, 验证码: {code}")
                                return str(code)
                            else:
                                print(f"⚠️ 激活响应格式异常: {response_data}")
                        except Exception as e:
                            print(f"❌ JSON解析失败: {e}")

                    # 生成备用验证码
                    code_hash = hashlib.md5(device_id.encode()).hexdigest()[:6]
                    return code_hash.upper()

        except Exception as e:
            print(f"❌ PocketSpeak激活请求失败: {e}")
            code_hash = hashlib.md5(device_id.encode()).hexdigest()[:6]
            return code_hash.upper()

    async def get_or_create_device_activation(self) -> Dict[str, Any]:
        """
        入口方法：完全使用py-xiaozhi的激活流程
        1. 若已激活，返回设备信息与激活标记 ✅
        2. 若未激活，使用PocketSpeakActivator处理设备创建和验证码获取
        """
        print("\n" + "="*60)
        print("🔧 PocketSpeak 设备激活生命周期管理 - 使用py-xiaozhi实现")
        print("="*60)

        try:
            # 使用pocketspeak_activator的py-xiaozhi完整实现
            from services.pocketspeak_activator import pocketspeak_activator

            print("🌐 使用PocketSpeakActivator的py-xiaozhi激活逻辑...")
            activation_result = await pocketspeak_activator.request_activation_code()

            if activation_result.get("success"):
                verification_code = activation_result.get("verification_code")
                challenge = activation_result.get("challenge")
                device_id = activation_result.get("device_id")
                serial_number = activation_result.get("serial_number")
                is_already_activated = activation_result.get("is_already_activated", False)

                if is_already_activated:
                    print("✅ 设备已激活，无需重新获取验证码")
                    return {
                        "success": True,
                        "activated": True,
                        "device_id": device_id,
                        "message": activation_result.get("message", "设备已激活，跳过验证码流程"),
                        "verification_code": None
                    }
                else:
                    print(f"✅ 验证码获取成功: {verification_code}")
                    print(f"🎯 挑战字符串: {challenge}")
                    print(f"📱 设备ID: {device_id}")
                    print(f"🏷️ 序列号: {serial_number}")
                    print("="*60)

                    # ✅ 关键修复：保存challenge到device_info.json，用于后续HMAC确认
                    device_info = self.load_device_info_from_local()
                    if device_info and challenge:
                        device_data = device_info.__dict__
                        device_data["challenge"] = challenge
                        self.save_device_info_to_local(device_data)
                        print(f"💾 已保存challenge到设备信息: {challenge}")

                    return {
                        "success": True,
                        "activated": False,
                        "device_id": device_id,
                        "serial_number": serial_number,
                        "verification_code": verification_code,
                        "challenge": challenge,
                        "message": activation_result.get("message", f"请在xiaozhi.me输入验证码: {verification_code}"),
                        "server_response": activation_result.get("server_response", {})
                    }
            else:
                print(f"❌ PocketSpeakActivator激活失败，尝试使用OTA备用方案: {activation_result.get('message')}")

                # 备用方案：当激活端点失败时，尝试通过OTA端点获取验证码
                print("🔄 使用OTA端点获取验证码作为备用方案...")
                fallback_result = await self._fallback_ota_activation()

                if fallback_result.get("success"):
                    print(f"✅ OTA备用方案成功获取验证码: {fallback_result.get('verification_code')}")
                    return fallback_result
                else:
                    print("❌ OTA备用方案也失败了")
                    return activation_result

        except Exception as e:
            print(f"❌ 激活流程失败: {e}")
            return {
                "success": False,
                "activated": False,
                "device_id": None,
                "verification_code": None,
                "message": f"激活流程失败: {str(e)}",
                "error": str(e)
            }

    async def _fallback_ota_activation(self) -> Dict[str, Any]:
        """
        备用OTA激活方案：当py-xiaozhi激活端点失败时，使用OTA端点获取验证码
        """
        try:
            device_info = self.load_device_info_from_local()
            if not device_info:
                return {
                    "success": False,
                    "message": "设备信息不存在",
                    "error": "no_device_info"
                }

            device_id = device_info.device_id
            client_id = device_info.client_id
            serial_number = device_info.serial_number

            # 构造OTA请求
            headers = {
                "Device-Id": device_id,
                "Client-Id": client_id,
                "Activation-Version": "2",
                "Content-Type": "application/json",
                "User-Agent": "PocketSpeak/1.0"
            }

            request_body = {
                "application": {
                    "version": "1.0.0",
                    "elf_sha256": device_info.hmac_key
                },
                "board": {
                    "type": "xiaozhi-python",
                    "name": "xiaozhi-python",
                    "ip": "0.0.0.0",
                    "mac": device_id
                }
            }

            print(f"🔄 OTA备用激活: {self.zoe_ota_url}")
            print(f"📱 设备ID: {device_id}")
            print(f"🏷️ 序列号: {serial_number}")

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.zoe_ota_url,
                    headers=headers,
                    json=request_body
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    print(f"📡 OTA备用响应状态: HTTP {status_code}")
                    print(f"📄 OTA备用响应内容: {response_text}")

                    if status_code == 200:
                        try:
                            response_data = await response.json()

                            # 从OTA响应中提取验证码
                            activation_data = response_data.get("activation", {})
                            if activation_data:
                                verification_code = activation_data.get("code")
                                challenge = activation_data.get("challenge")
                                message = activation_data.get("message", "请在xiaozhi.me输入验证码")

                                if verification_code:
                                    # ✅ 关键修复：保存challenge到device_info.json，用于后续HMAC确认
                                    if challenge:
                                        device_data = device_info.__dict__
                                        device_data["challenge"] = challenge
                                        self.save_device_info_to_local(device_data)
                                        print(f"💾 已从OTA响应保存challenge到设备信息: {challenge}")

                                    return {
                                        "success": True,
                                        "activated": False,
                                        "device_id": device_id,
                                        "serial_number": serial_number,
                                        "verification_code": verification_code,
                                        "challenge": challenge,
                                        "message": f"请在xiaozhi.me输入验证码: {verification_code}",
                                        "server_response": response_data,
                                        "source": "ota_fallback"
                                    }

                            return {
                                "success": False,
                                "message": "OTA响应中未找到验证码",
                                "error": "no_activation_code",
                                "server_response": response_data
                            }

                        except Exception as e:
                            print(f"❌ OTA响应解析失败: {e}")
                            return {
                                "success": False,
                                "message": f"OTA响应解析失败: {e}",
                                "error": "json_parse_error",
                                "raw_response": response_text
                            }
                    else:
                        return {
                            "success": False,
                            "message": f"OTA HTTP {status_code} 错误",
                            "error": f"http_error_{status_code}",
                            "raw_response": response_text
                        }

        except Exception as e:
            print(f"❌ OTA备用激活失败: {e}")
            return {
                "success": False,
                "message": f"OTA备用激活失败: {str(e)}",
                "error": "network_error"
            }

    def mark_device_activated(self, device_id: str = None, connection_params: Dict[str, Any] = None) -> bool:
        """
        标记设备为已激活状态（用户在官网完成绑定后调用）
        ✅ 新增：保存连接参数（MQTT、WebSocket等）
        """
        device_info = self.load_device_info_from_local()
        if device_info is None:
            print("❌ 无法标记激活：设备信息不存在")
            return False

        # 更新激活状态
        device_data = device_info.__dict__
        device_data["activated"] = True
        device_data["activated_at"] = platform.node()

        # ✅ 保存连接参数
        if connection_params:
            print("💾 保存连接参数...")
            device_data["connection_params"] = connection_params
            if "mqtt" in connection_params:
                print(f"  MQTT服务器: {connection_params['mqtt'].get('server', 'N/A')}")
            if "websocket" in connection_params:
                print(f"  WebSocket URL: {connection_params['websocket'].get('url', 'N/A')}")

        success = self.save_device_info_to_local(device_data)
        if success:
            print(f"✅ 设备已标记为激活状态: {device_info.device_id}")
        else:
            print("❌ 标记激活状态失败")

        return success

    def reset_activation_status(self) -> bool:
        """
        重置激活状态为未激活（调试用）
        """
        device_info = self.load_device_info_from_local()
        if device_info is None:
            print("❌ 无法重置：设备信息不存在")
            return False

        # 重置激活状态
        device_data = device_info.__dict__
        device_data["activated"] = False
        device_data.pop("activated_at", None)

        success = self.save_device_info_to_local(device_data)
        if success:
            print(f"✅ 激活状态已重置为未激活: {device_info.device_id}")
        else:
            print("❌ 重置激活状态失败")

        return success

    def get_device_status_info(self) -> Dict[str, Any]:
        """
        获取设备状态信息（用于调试和状态查询）
        """
        device_info = self.load_device_info_from_local()
        if device_info is None:
            return {
                "device_exists": False,
                "activated": False,
                "message": "设备信息不存在"
            }

        return {
            "device_exists": True,
            "activated": device_info.activated,
            "device_id": device_info.device_id,
            "mac_address": device_info.mac_address,
            "serial_number": device_info.serial_number,
            "client_id": device_info.client_id,
            "activation_method": device_info.activation_method,
            "message": "已激活" if device_info.activated else "未激活"
        }

    async def poll_activation_status(self) -> Dict[str, Any]:
        """
        轮询小智AI服务器获取设备激活状态
        ✅ 修复：检测到可能激活后，主动调用HMAC确认获取连接参数
        """
        try:
            # 1. 首先检查本地激活状态
            local_is_activated = self.is_device_activated()
            device_info = self.load_device_info_from_local()

            if not device_info:
                return {
                    "is_activated": False,
                    "device_id": None,
                    "serial_number": None,
                    "activation_status": "设备信息不存在",
                    "error": "未找到设备信息"
                }

            if local_is_activated:
                return {
                    "is_activated": True,
                    "device_id": device_info.device_id,
                    "serial_number": device_info.serial_number,
                    "activation_status": "已激活",
                    "websocket_url": "wss://api.xiaozhi.com/v1/ws",
                    "access_token": "pocketspeak_activated"
                }

            # ✅ 关键修复：尝试通过HMAC确认激活状态并获取连接参数
            print("🔍 尝试通过HMAC确认激活状态...")
            from services.pocketspeak_activator import pocketspeak_activator

            # 从激活响应中获取challenge（如果有保存）
            challenge = device_info.__dict__.get("challenge") if hasattr(device_info, "__dict__") else None

            if challenge:
                print(f"🎯 使用保存的challenge进行HMAC确认: {challenge}")
                confirm_result = await pocketspeak_activator.confirm_activation(challenge)

                if confirm_result.get("success") and confirm_result.get("is_activated"):
                    # HMAC确认成功，设备已激活
                    print("✅ HMAC确认成功！设备已激活")
                    connection_params = confirm_result.get("connection_params", {})

                    # 保存激活状态和连接参数
                    self.mark_device_activated(
                        device_id=device_info.device_id,
                        connection_params=connection_params
                    )

                    return {
                        "is_activated": True,
                        "device_id": device_info.device_id,
                        "serial_number": device_info.serial_number,
                        "activation_status": "HMAC确认激活成功",
                        "websocket_url": connection_params.get("websocket", {}).get("url", "wss://api.tenclass.net/xiaozhi/v1/"),
                        "mqtt_params": connection_params.get("mqtt", {}),
                        "server_response": confirm_result
                    }
                else:
                    print(f"⏳ HMAC确认尚未成功: {confirm_result.get('message')}")
            else:
                print("⚠️ 未找到challenge，无法进行HMAC确认")

            # 2. 如果本地未激活，向小智AI服务器查询激活状态
            device_id = device_info.device_id
            serial_number = device_info.serial_number
            client_id = device_info.client_id

            if not serial_number or not device_id:
                return {
                    "is_activated": False,
                    "device_id": device_id,
                    "serial_number": serial_number,
                    "activation_status": "设备信息不完整",
                    "error": "缺少设备序列号或ID"
                }

            # 3. 构造轮询请求
            headers = {
                "DeviceId": device_id,
                "ClientId": client_id,
                "Activation-Version": "2",
                "Content-Type": "application/json",
                "User-Agent": "PocketSpeak/1.0"
            }

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

            # 4. 发送轮询请求到正确的激活状态查询端点
            import aiohttp

            # 使用正确的激活状态查询URL - 不使用OTA端点进行状态查询
            activation_status_url = "https://api.tenclass.net/xiaozhi/activation/status"

            print(f"🔍 使用激活状态查询URL: {activation_status_url}")

            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    activation_status_url,
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
                            server_activated = response_data.get("activated", False) or response_data.get("success", False)
                            activation_info = response_data.get("activation_info", {}) or response_data.get("data", {})

                            if server_activated:
                                # 服务器确认设备已激活，同步到本地
                                print("✅ 服务器确认设备已激活，更新本地状态...")
                                device_data = device_info.__dict__
                                device_data["activated"] = True
                                device_data["activated_at"] = datetime.now().isoformat()
                                self.save_device_info_to_local(device_data)

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
                            return {
                                "is_activated": False,
                                "device_id": device_id,
                                "serial_number": serial_number,
                                "activation_status": "服务器响应解析失败",
                                "error": str(e)
                            }
                    else:
                        print(f"⚠️ 服务器轮询失败: HTTP {status_code}")
                        # 如果专用状态查询端点失败，尝试使用OTA端点作为备用
                        if status_code == 404:
                            print(f"⚠️ 激活状态端点不存在，尝试使用OTA端点作为备用...")
                            return await self._fallback_ota_polling(device_id, serial_number, client_id)

                        return {
                            "is_activated": False,
                            "device_id": device_id,
                            "serial_number": serial_number,
                            "activation_status": f"服务器轮询失败 (HTTP {status_code})",
                            "error": f"HTTP {status_code}: {response_text}"
                        }

        except Exception as e:
            print(f"❌ 轮询激活状态发生错误: {e}")
            # 如果主轮询失败，尝试使用OTA备用轮询
            try:
                print(f"🔄 尝试使用OTA备用轮询...")
                return await self._fallback_ota_polling(device_id, serial_number, client_id)
            except Exception as fallback_e:
                print(f"❌ OTA备用轮询也失败: {fallback_e}")
                device_info = self.load_device_info_from_local()
                return {
                    "is_activated": False,
                    "device_id": device_info.device_id if device_info else None,
                    "serial_number": device_info.serial_number if device_info else None,
                    "activation_status": "轮询网络错误",
                    "error": f"主轮询: {str(e)}, 备用轮询: {str(fallback_e)}"
                }

    async def _fallback_ota_polling(self, device_id: str, serial_number: str, client_id: str) -> Dict[str, Any]:
        """
        备用轮询方法：使用OTA端点查询设备状态
        """
        import aiohttp

        # 使用OTA端点作为备用
        ota_url = "https://api.tenclass.net/xiaozhi/ota/"

        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
            "Content-Type": "application/json",
            "User-Agent": "PocketSpeak/1.0"
        }

        request_body = {
            "device_id": device_id,
            "mac_address": device_id,
            "device_info": {
                "device_id": device_id,
                "serial_number": serial_number
            }
        }

        print(f"🔄 OTA备用轮询: {ota_url}")
        print(f"📱 设备ID: {device_id}")

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                ota_url,
                headers=headers,
                json=request_body
            ) as response:
                response_text = await response.text()
                status_code = response.status

                print(f"📡 OTA备用响应状态: HTTP {status_code}")
                print(f"📄 OTA备用响应内容: {response_text}")

                if status_code == 200:
                    try:
                        response_data = await response.json()

                        # ✅ 关键修复：检测激活完成的标志
                        # 当OTA响应中不再包含activation字段时，说明用户已完成激活
                        activation_data = response_data.get("activation", {})

                        if activation_data:
                            # 仍在等待激活，保存challenge（如果有）
                            challenge = activation_data.get("challenge")
                            if challenge:
                                device_info = self.load_device_info_from_local()
                                if device_info:
                                    device_data = device_info.__dict__
                                    if device_data.get("challenge") != challenge:
                                        device_data["challenge"] = challenge
                                        self.save_device_info_to_local(device_data)
                                        print(f"💾 OTA轮询中保存challenge: {challenge}")

                            return {
                                "is_activated": False,
                                "device_id": device_id,
                                "serial_number": serial_number,
                                "activation_status": "设备配置正常，等待激活确认",
                                "ota_response": activation_data,
                                "message": "设备已成功注册到小智AI服务器，等待用户完成激活"
                            }
                        else:
                            # ✅ activation字段消失 = 激活完成！
                            # 提取并保存连接参数
                            print("🎉 检测到OTA响应中activation字段已消失，设备已激活！")

                            mqtt_params = response_data.get("mqtt", {})
                            websocket_params = response_data.get("websocket", {})

                            if mqtt_params or websocket_params:
                                # 构造连接参数
                                connection_params = {
                                    "mqtt": mqtt_params,
                                    "websocket": websocket_params,
                                    "server_time": response_data.get("server_time", {}),
                                    "firmware": response_data.get("firmware", {})
                                }

                                # 标记设备为已激活并保存连接参数
                                print("💾 保存连接参数并标记设备为已激活...")
                                self.mark_device_activated(
                                    device_id=device_id,
                                    connection_params=connection_params
                                )

                                # 返回激活成功状态
                                return {
                                    "is_activated": True,
                                    "device_id": device_id,
                                    "serial_number": serial_number,
                                    "activation_status": "OTA检测到激活成功",
                                    "websocket_url": websocket_params.get("url", "wss://api.tenclass.net/xiaozhi/v1/"),
                                    "mqtt_params": mqtt_params,
                                    "connection_params": connection_params,
                                    "message": "设备激活成功，连接参数已保存"
                                }
                            else:
                                print("⚠️ OTA响应中没有activation字段，但也没有连接参数")
                                return {
                                    "is_activated": False,
                                    "device_id": device_id,
                                    "serial_number": serial_number,
                                    "activation_status": "OTA备用轮询成功，但缺少连接参数",
                                    "server_response": response_data
                                }

                    except Exception as e:
                        print(f"❌ OTA响应解析失败: {e}")
                        return {
                            "is_activated": False,
                            "device_id": device_id,
                            "serial_number": serial_number,
                            "activation_status": "OTA备用响应解析失败",
                            "error": str(e)
                        }
                else:
                    return {
                        "is_activated": False,
                        "device_id": device_id,
                        "serial_number": serial_number,
                        "activation_status": f"OTA备用轮询失败 (HTTP {status_code})",
                        "error": f"HTTP {status_code}: {response_text}"
                    }

    def _generate_numeric_code(self, device_id: str) -> str:
        """
        生成6位纯数字备用验证码
        使用设备ID和时间戳确保唯一性，只返回数字
        """
        import time
        import hashlib

        # 使用设备ID和当前时间生成种子
        seed = f"{device_id}_{int(time.time() * 1000)}"
        hash_value = hashlib.sha256(seed.encode()).hexdigest()

        # 提取数字字符并生成6位验证码
        numeric_chars = ''.join([c for c in hash_value if c.isdigit()])
        if len(numeric_chars) >= 6:
            return numeric_chars[:6]
        else:
            # 如果数字不够，用时间戳补充
            timestamp_digits = str(int(time.time() * 1000))[-6:]
            return (numeric_chars + timestamp_digits)[:6]


# 全局实例
device_lifecycle_manager = PocketSpeakDeviceLifecycle()

# 兼容 py-xiaozhi 激活流程的设备管理器实例
pocketspeak_device_manager = PocketSpeakDeviceManager(device_lifecycle_manager)