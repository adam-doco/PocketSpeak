"""
PocketSpeak 设备生命周期管理 - 完全复刻py-xiaozhi激活逻辑
严格按照py-xiaozhi的efuse.json存储和激活判断机制实现
"""

import json
import hashlib
import hmac
import random
import uuid
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import psutil
import aiohttp

class PocketSpeakDeviceManager:
    """完全复刻py-xiaozhi的设备生命周期管理逻辑"""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.device_info_file = self.storage_dir / "device_info.json"
        self._device_cache: Optional[Dict] = None

    def _get_real_mac_address(self) -> Optional[str]:
        """获取系统真实MAC地址 - 复刻py-xiaozhi逻辑"""
        try:
            # 获取网络接口信息
            net_interfaces = psutil.net_if_addrs()

            for interface_name, interface_addresses in net_interfaces.items():
                # 跳过回环接口
                if interface_name.lower() in ['lo', 'loopback']:
                    continue

                for address in interface_addresses:
                    # 查找MAC地址
                    if hasattr(address, 'family') and address.family.name == 'AF_LINK':
                        mac = address.address
                        if mac and mac != "00:00:00:00:00:00":
                            return self._normalize_mac_address(mac)

            return None
        except Exception as e:
            print(f"获取MAC地址失败: {e}")
            return None

    def _normalize_mac_address(self, mac_address: str) -> str:
        """标准化MAC地址格式为小写冒号分隔格式 - 复刻py-xiaozhi"""
        if not mac_address:
            return mac_address

        # 移除所有可能的分隔符，只保留十六进制字符
        clean_mac = "".join(c for c in mac_address if c.isalnum())

        # 确保长度为12个字符
        if len(clean_mac) != 12:
            return mac_address

        # 转换为小写并添加冒号分隔符
        clean_mac = clean_mac.lower()
        formatted_mac = ":".join([clean_mac[i:i+2] for i in range(0, 12, 2)])

        return formatted_mac

    def _generate_serial_number(self, mac_address: str) -> str:
        """生成序列号 - 完全复刻py-xiaozhi格式"""
        if not mac_address:
            return None

        # 清理MAC地址
        mac_clean = mac_address.lower().replace(":", "")

        # 生成MD5哈希的前8位作为短哈希
        short_hash = hashlib.md5(mac_clean.encode()).hexdigest()[:8].upper()

        # 生成序列号：SN-{short_hash}-{mac_clean}
        serial_number = f"SN-{short_hash}-{mac_clean}"

        return serial_number

    def _generate_hmac_key(self) -> str:
        """生成HMAC密钥 - 64位十六进制字符串"""
        return ''.join(f"{random.randint(0, 255):02x}" for _ in range(32))

    def _generate_device_fingerprint(self) -> Dict[str, Any]:
        """生成设备指纹信息"""
        return {
            "hostname": platform.node(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }

    def _load_device_info(self) -> Dict[str, Any]:
        """加载设备信息 - 对应py-xiaozhi的_load_efuse_data"""
        if self._device_cache is not None:
            return self._device_cache

        if not self.device_info_file.exists():
            return self._create_default_device_info()

        try:
            with open(self.device_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._device_cache = data
                return data
        except Exception as e:
            print(f"加载设备信息失败: {e}")
            return self._create_default_device_info()

    def _create_default_device_info(self) -> Dict[str, Any]:
        """创建默认设备信息 - 对应py-xiaozhi的efuse结构"""
        return {
            "mac_address": None,
            "serial_number": None,
            "hmac_key": None,
            "activation_status": False,  # 关键字段 - 默认未激活
            "device_fingerprint": {},
            "device_id": None,
            "client_id": None
        }

    def _save_device_info(self, data: Dict[str, Any]) -> bool:
        """保存设备信息 - 对应py-xiaozhi的_save_efuse_data"""
        try:
            with open(self.device_info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 更新缓存
            self._device_cache = data
            print(f"设备信息已保存: {self.device_info_file}")
            return True
        except Exception as e:
            print(f"保存设备信息失败: {e}")
            return False

    def check_activation_status(self) -> bool:
        """检查设备是否已激活 - 对应py-xiaozhi的is_activated"""
        device_info = self._load_device_info()
        return device_info.get("activation_status", False)

    def ensure_device_identity(self) -> Tuple[Optional[str], Optional[str], bool]:
        """确保设备身份信息存在 - 对应py-xiaozhi的ensure_device_identity"""
        device_info = self._load_device_info()

        # 检查是否需要生成新的设备身份
        if not all([
            device_info.get("mac_address"),
            device_info.get("serial_number"),
            device_info.get("hmac_key")
        ]):
            # 生成新的设备身份
            mac_address = self._get_real_mac_address()
            if not mac_address:
                print("无法获取MAC地址")
                return None, None, False

            device_info.update({
                "mac_address": mac_address,
                "serial_number": self._generate_serial_number(mac_address),
                "hmac_key": self._generate_hmac_key(),
                "device_fingerprint": self._generate_device_fingerprint(),
                "device_id": mac_address,  # PocketSpeak使用MAC作为设备ID
                "client_id": str(uuid.uuid4())
            })

            self._save_device_info(device_info)

        return (
            device_info.get("serial_number"),
            device_info.get("hmac_key"),
            device_info.get("activation_status", False)
        )

    def get_device_info(self) -> Dict[str, Any]:
        """获取完整设备信息"""
        return self._load_device_info()

    def get_device_id(self) -> Optional[str]:
        """获取设备ID（MAC地址）"""
        device_info = self._load_device_info()
        return device_info.get("device_id") or device_info.get("mac_address")

    def get_client_id(self) -> Optional[str]:
        """获取客户端ID"""
        device_info = self._load_device_info()
        return device_info.get("client_id")

    def get_serial_number(self) -> Optional[str]:
        """获取序列号"""
        device_info = self._load_device_info()
        return device_info.get("serial_number")

    def get_hmac_key(self) -> Optional[str]:
        """获取HMAC密钥"""
        device_info = self._load_device_info()
        return device_info.get("hmac_key")

    def generate_hmac_signature(self, challenge: str) -> Optional[str]:
        """生成HMAC签名 - 对应py-xiaozhi的generate_hmac"""
        if not challenge:
            return None

        hmac_key = self.get_hmac_key()
        if not hmac_key:
            return None

        try:
            signature = hmac.new(
                hmac_key.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            print(f"生成HMAC签名失败: {e}")
            return None

    def mark_device_as_activated(self) -> bool:
        """将设备标记为已激活 - 对应py-xiaozhi的set_activation_status(True)"""
        device_info = self._load_device_info()
        device_info["activation_status"] = True
        return self._save_device_info(device_info)

    def reset_activation_status(self) -> bool:
        """重置激活状态为未激活（调试用）"""
        device_info = self._load_device_info()
        device_info["activation_status"] = False
        return self._save_device_info(device_info)

    def print_device_info(self):
        """打印设备信息"""
        device_info = self.get_device_info()
        is_activated = self.check_activation_status()

        print("\n" + "="*60)
        print("🔧 PocketSpeak 设备信息")
        print("="*60)
        print(f"📱 设备ID: {device_info.get('device_id', 'None')}")
        print(f"🌐 MAC地址: {device_info.get('mac_address', 'None')}")
        print(f"🏷️ 序列号: {device_info.get('serial_number', 'None')}")
        print(f"🆔 客户端ID: {device_info.get('client_id', 'None')}")
        print(f"🔑 HMAC密钥: {device_info.get('hmac_key', 'None')[:16] if device_info.get('hmac_key') else 'None'}...")
        print(f"✅ 激活状态: {'已激活' if is_activated else '未激活'}")
        print("="*60)


# 全局实例
pocketspeak_device_manager = PocketSpeakDeviceManager()