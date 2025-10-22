"""
PocketSpeak Backend 主程序入口
FastAPI 应用程序启动和配置
"""

# 必须在导入其他模块之前初始化路径
import setup_paths  # noqa: F401

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import settings
from routers import device, ws_lifecycle, voice_chat, user, auth_router, word_router, audio_proxy, word_lookup_v2
from core.device_manager import print_device_debug_info

# 配置应用日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时执行
    print("\n🚀 PocketSpeak Backend 正在启动...")
    print(f"📱 应用名称: {settings.app_name}")
    print(f"🔢 版本: {settings.version}")

    # 打印设备调试信息
    print_device_debug_info()

    yield

    # 关闭时执行
    print("\n👋 PocketSpeak Backend 正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(device.router)
app.include_router(ws_lifecycle.router)
app.include_router(voice_chat.router)
app.include_router(user.router)  # V1.2: 用户管理路由
app.include_router(auth_router.router)  # V1.3: 认证路由
app.include_router(word_router.router)  # V1.5: 单词查询与生词本路由（旧版）
app.include_router(word_lookup_v2.router)  # V1.5.1: AI驱动的单词查询路由（新版）
app.include_router(audio_proxy.router)  # V1.5: 音频代理路由


# 根路径
@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "app": settings.app_name,
        "version": settings.version,
        "status": "running",
        "message": "PocketSpeak Backend API 正在运行"
    }


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "PocketSpeak Backend",
        "version": settings.version
    }


if __name__ == "__main__":
    print(f"\n🌟 启动 {settings.app_name}")
    print(f"🔧 调试模式: {'开启' if settings.debug else '关闭'}")
    print(f"🌐 服务地址: http://{settings.host}:{settings.port}")
    print(f"📚 API文档: http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level
    )