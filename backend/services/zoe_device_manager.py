"""
Zoe风格设备管理器 - 完全复刻Zoe项目的设备绑定实现
严格按照https://github.com/adam-doco/Zoe/blob/Zoev4/xiaozhi.py实现
"""

import hashlib
import hmac
import random
import uuid
import json
from typing import Dict, Any, Optional
from pathlib import Path

class ZoeDeviceManager:
    """完全复刻Zoe项目的设备管理逻辑"""

    def __init__(self):
        self.config_dir = Path.cwd() / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file = self.config_dir / "zoe_device_identity.json"
        self._identity = None

    def _generate_virtual_mac(self) -> str:
        """生成虚拟MAC地址 - 02:00:00:xx:xx:xx格式 - 完全复刻Zoe实现"""
        def random_byte() -> str:
            return f"{random.randint(0, 255):02x}"

        return f"02:00:00:{random_byte()}:{random_byte()}:{random_byte()}"

    def _generate_serial(self, mac: str) -> str:
        """生成设备序列号 - 完全复刻Zoe实现"""
        seed = ''.join(f"{random.randint(0, 255):02X}" for _ in range(4))
        mac_hex = mac.replace(':', '').upper()
        tail = mac_hex[-12:] if len(mac_hex) >= 12 else mac_hex.ljust(12, '0')
        return f"SN-{seed}-{tail}"

    def _generate_hmac_key(self) -> str:
        """生成HMAC密钥 - 64位十六进制字符串"""
        return ''.join(f"{random.randint(0, 255):02x}" for _ in range(32))

    @staticmethod
    def hmac_sha256_hex(key_hex: str, data: str) -> str:
        """计算HMAC-SHA256签名 - 完全复刻Zoe实现"""
        try:
            key_bytes = bytes.fromhex(key_hex)
            signature = hmac.new(key_bytes, data.encode('utf-8'), hashlib.sha256)
            return signature.hexdigest()
        except Exception as e:
            print(f"HMAC计算失败: {e}")
            return ""

    def get_or_create_identity(self) -> Dict[str, Any]:
        """获取或创建设备身份信息"""
        if self._identity is None:
            if self.identity_file.exists():
                try:
                    with open(self.identity_file, 'r', encoding='utf-8') as f:
                        self._identity = json.load(f)
                        print(f"从文件加载设备身份: {self.identity_file}")
                except Exception as e:
                    print(f"加载设备身份失败: {e}")
                    self._identity = None

            if self._identity is None:
                # 创建新的设备身份
                mac = self._generate_virtual_mac()
                self._identity = {
                    "device_id": mac,
                    "client_id": str(uuid.uuid4()),
                    "serial_number": self._generate_serial(mac),
                    "hmac_key_hex": self._generate_hmac_key()
                }

                # 保存到文件
                try:
                    with open(self.identity_file, 'w', encoding='utf-8') as f:
                        json.dump(self._identity, f, indent=2, ensure_ascii=False)
                    print(f"创建新设备身份: {self.identity_file}")
                except Exception as e:
                    print(f"保存设备身份失败: {e}")

        return self._identity

    def get_device_id(self) -> str:
        """获取设备ID（虚拟MAC地址）"""
        identity = self.get_or_create_identity()
        return identity["device_id"]

    def get_client_id(self) -> str:
        """获取客户端ID"""
        identity = self.get_or_create_identity()
        return identity["client_id"]

    def get_serial_number(self) -> str:
        """获取序列号"""
        identity = self.get_or_create_identity()
        return identity["serial_number"]

    def get_hmac_key(self) -> str:
        """获取HMAC密钥"""
        identity = self.get_or_create_identity()
        return identity["hmac_key_hex"]

    def print_identity_info(self):
        """打印设备身份信息"""
        identity = self.get_or_create_identity()
        print("\n" + "="*50)
        print("🔧 Zoe设备身份信息")
        print("="*50)
        print(f"📱 设备ID: {identity['device_id']}")
        print(f"🆔 客户端ID: {identity['client_id']}")
        print(f"🏷️ 序列号: {identity['serial_number']}")
        print(f"🔑 HMAC密钥: {identity['hmac_key_hex'][:16]}...")
        print("="*50)


# 全局实例
zoe_device_manager = ZoeDeviceManager()