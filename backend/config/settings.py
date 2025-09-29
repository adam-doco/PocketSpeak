"""
PocketSpeak Backend Configuration Settings
配置管理模块，负责加载环境变量和项目设置
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用程序设置类"""

    # 小智AI服务配置
    xiaozhi_base_url: str = os.getenv("XIAOZHI_BASE_URL", "https://xiaozhi.me")
    xiaozhi_ota_url: str = os.getenv("XIAOZHI_OTA_URL", "https://api.tenclass.net/xiaozhi/ota/")
    xiaozhi_ws_url: str = os.getenv("XIAOZHI_WS_URL", "wss://api.xiaozhi.com/v1/ws")
    xiaozhi_api_url: str = os.getenv("XIAOZHI_API_URL", "https://api.xiaozhi.com")

    # 服务器配置
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "info")
    log_file: str = os.getenv("LOG_FILE", "logs/pocketspeak.log")

    # 项目信息
    app_name: str = "PocketSpeak Backend"
    version: str = "1.0.0"
    description: str = "PocketSpeak AI English Learning Assistant Backend"

    class Config:
        env_file = ".env"

# 全局设置实例
settings = Settings()