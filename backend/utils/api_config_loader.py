# -*- coding: utf-8 -*-
"""
API配置加载器 - PocketSpeak V1.5
从 YAML 文件中加载第三方API配置
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class APIConfigLoader:
    """API配置加载器"""

    def __init__(self):
        """初始化配置加载器"""
        # 配置文件路径
        backend_dir = Path(__file__).parent.parent
        self.config_file = backend_dir / "config" / "external_apis.yaml"

        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        try:
            if not self.config_file.exists():
                print(f"⚠️ 配置文件不存在: {self.config_file}")
                return {}

            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                print(f"✅ API配置加载成功: {self.config_file}")
                return config or {}

        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置（V1.5.1新增）"""
        return self.config

    def get_youdao_config(self) -> Dict[str, Any]:
        """获取有道API配置"""
        return self.config.get('youdao', {})

    def is_youdao_enabled(self) -> bool:
        """检查有道API是否启用"""
        youdao_config = self.get_youdao_config()
        return youdao_config.get('enabled', False)


# 创建全局单例
api_config_loader = APIConfigLoader()
