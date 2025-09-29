"""
PocketSpeak 设备管理模块
负责封装 py-xiaozhi 的设备功能，生成设备ID和管理设备信息
"""

import sys
import os
import json
import hashlib
from typing import Dict, Optional, Tuple
from pathlib import Path

# 添加 py-xiaozhi 模块到 Python 路径
current_dir = Path(__file__).parent.parent
py_xiaozhi_path = current_dir / "libs" / "py_xiaozhi" / "src"
sys.path.insert(0, str(py_xiaozhi_path))

try:
    from utils.device_fingerprint import DeviceFingerprint
except ImportError as e:
    print(f"警告: 无法导入 py-xiaozhi 模块: {e}")
    DeviceFingerprint = None

# 导入py-machineid
try:
    import machineid
except ImportError:
    machineid = None

from config.settings import settings


class DeviceManager:
    """设备管理器 - 封装 py-xiaozhi 的设备功能"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化设备管理器"""
        if self._initialized:
            return

        self._initialized = True
        self._device_fingerprint = None
        self._device_cache = None

        # 初始化 py-xiaozhi 设备指纹组件（如果可用）
        self._init_device_fingerprint()

    def _init_device_fingerprint(self):
        """初始化设备指纹组件"""
        if DeviceFingerprint is not None:
            try:
                self._device_fingerprint = DeviceFingerprint.get_instance()
                print("✅ py-xiaozhi 设备指纹组件初始化成功")
            except Exception as e:
                print(f"⚠️ py-xiaozhi 设备指纹组件初始化失败: {e}")
                self._device_fingerprint = None
        else:
            print("⚠️ py-xiaozhi 模块不可用，使用备用设备ID生成方案")

    def generate_device_id(self) -> str:
        """
        生成设备ID
        优先使用 py-xiaozhi 的设备指纹生成，否则使用备用方案

        Returns:
            str: 唯一的设备ID
        """
        if self._device_cache:
            return self._device_cache.get("device_id", self._generate_fallback_device_id())

        if self._device_fingerprint:
            try:
                # 使用 py-xiaozhi 生成设备指纹
                fingerprint = self._device_fingerprint.generate_fingerprint()
                hardware_hash = self._device_fingerprint.generate_hardware_hash()

                device_id = f"PS-{hardware_hash[:12].upper()}"

                # 缓存设备信息
                self._device_cache = {
                    "device_id": device_id,
                    "fingerprint": fingerprint,
                    "hardware_hash": hardware_hash,
                    "source": "py-xiaozhi"
                }

                return device_id
            except Exception as e:
                print(f"使用 py-xiaozhi 生成设备ID失败: {e}")
                return self._generate_fallback_device_id()
        else:
            return self._generate_fallback_device_id()

    def _generate_fallback_device_id(self) -> str:
        """
        备用设备ID生成方案（当 py-xiaozhi 不可用时）

        Returns:
            str: 备用设备ID
        """
        import platform
        import uuid

        # 获取基本系统信息
        system_info = {
            "hostname": platform.node(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }

        # 尝试获取MAC地址和机器ID
        try:
            mac = hex(uuid.getnode())[2:]
            system_info["mac"] = mac
        except Exception:
            system_info["mac"] = "unknown"

        # 尝试获取机器ID
        if machineid:
            try:
                system_info["machine_id"] = machineid.id()
            except Exception:
                system_info["machine_id"] = "unknown"
        else:
            system_info["machine_id"] = "unknown"

        # 生成哈希
        info_str = "|".join(f"{k}:{v}" for k, v in system_info.items())
        hash_obj = hashlib.sha256(info_str.encode('utf-8'))
        device_hash = hash_obj.hexdigest()[:12].upper()

        device_id = f"PS-FALLBACK-{device_hash}"

        # 缓存设备信息
        self._device_cache = {
            "device_id": device_id,
            "system_info": system_info,
            "device_hash": device_hash,
            "source": "fallback"
        }

        return device_id

    def get_device_info(self) -> Dict:
        """
        获取完整的设备信息

        Returns:
            Dict: 设备信息字典
        """
        if not self._device_cache:
            # 触发设备ID生成来填充缓存
            self.generate_device_id()

        return self._device_cache or {}

    def get_serial_number(self) -> Optional[str]:
        """
        获取设备序列号（如果使用 py-xiaozhi）

        Returns:
            Optional[str]: 设备序列号
        """
        if self._device_fingerprint:
            try:
                return self._device_fingerprint.get_serial_number()
            except Exception as e:
                print(f"获取序列号失败: {e}")
                return None
        return None

    def get_mac_address(self) -> Optional[str]:
        """
        获取MAC地址

        Returns:
            Optional[str]: MAC地址
        """
        if self._device_fingerprint:
            try:
                return self._device_fingerprint.get_mac_address()
            except Exception as e:
                print(f"获取MAC地址失败: {e}")
                return None
        else:
            # 备用方案
            try:
                import uuid
                mac = hex(uuid.getnode())[2:]
                # 格式化为标准MAC地址格式
                mac_formatted = ":".join(mac[i:i+2] for i in range(0, 12, 2))
                return mac_formatted
            except Exception:
                return None

    def is_activated(self) -> bool:
        """
        检查设备是否已激活（如果使用 py-xiaozhi）

        Returns:
            bool: 激活状态
        """
        if self._device_fingerprint:
            try:
                return self._device_fingerprint.is_activated()
            except Exception as e:
                print(f"检查激活状态失败: {e}")
                return False
        return False

    def ensure_device_identity(self) -> Tuple[Optional[str], Optional[str], bool]:
        """
        确保设备身份信息已创建（如果使用 py-xiaozhi）

        Returns:
            Tuple[Optional[str], Optional[str], bool]: (序列号, HMAC密钥, 激活状态)
        """
        if self._device_fingerprint:
            try:
                return self._device_fingerprint.ensure_device_identity()
            except Exception as e:
                print(f"确保设备身份失败: {e}")
                return None, None, False
        return None, None, False

    def print_device_debug_info(self):
        """打印设备调试信息"""
        print("\n" + "="*50)
        print("🔧 PocketSpeak 设备信息调试")
        print("="*50)

        device_id = self.generate_device_id()
        device_info = self.get_device_info()

        print(f"📱 设备ID: {device_id}")
        print(f"🔧 数据源: {device_info.get('source', 'unknown')}")

        if device_info.get('source') == 'py-xiaozhi':
            print(f"🔑 硬件哈希: {device_info.get('hardware_hash', 'N/A')}")
            serial_number = self.get_serial_number()
            if serial_number:
                print(f"🏷️ 序列号: {serial_number}")
            mac_address = self.get_mac_address()
            if mac_address:
                print(f"🌐 MAC地址: {mac_address}")
            print(f"✅ 激活状态: {'已激活' if self.is_activated() else '未激活'}")
        else:
            print(f"💻 系统信息: {device_info.get('system_info', {})}")

        print("="*50 + "\n")


# 全局设备管理器实例
device_manager = DeviceManager()


# 便捷函数
def generate_device_id() -> str:
    """生成设备ID的便捷函数"""
    return device_manager.generate_device_id()


def get_device_info() -> Dict:
    """获取设备信息的便捷函数"""
    return device_manager.get_device_info()


def print_device_debug_info():
    """打印设备调试信息的便捷函数"""
    device_manager.print_device_debug_info()


if __name__ == "__main__":
    # 测试模块
    print_device_debug_info()