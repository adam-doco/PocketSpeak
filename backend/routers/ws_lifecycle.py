"""
PocketSpeak WebSocket 生命周期管理路由

提供WebSocket连接的启动、停止、状态查询等API接口
"""

import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# 导入WebSocket客户端和设备管理器
from services.voice_chat.ws_client import (
    initialize_websocket_connection,
    get_websocket_client,
    get_connection_status,
    ConnectionState
)
from services.device_lifecycle import PocketSpeakDeviceLifecycle, PocketSpeakDeviceManager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/ws", tags=["WebSocket"])

# 全局设备管理器实例
_device_lifecycle_manager: PocketSpeakDeviceLifecycle = None
_device_manager: PocketSpeakDeviceManager = None


def initialize_device_managers():
    """初始化设备管理器"""
    global _device_lifecycle_manager, _device_manager

    if _device_lifecycle_manager is None:
        _device_lifecycle_manager = PocketSpeakDeviceLifecycle()
        logger.info("设备生命周期管理器已初始化")

    if _device_manager is None:
        _device_manager = PocketSpeakDeviceManager(_device_lifecycle_manager)
        logger.info("设备管理器已初始化")


# 响应模型
class WebSocketResponse(BaseModel):
    """WebSocket操作响应模型"""
    success: bool
    message: str
    data: Dict[str, Any] = {}


class WebSocketStatusResponse(BaseModel):
    """WebSocket状态响应模型"""
    success: bool
    data: Dict[str, Any]


@router.post("/start", response_model=WebSocketResponse)
async def start_websocket_connection(background_tasks: BackgroundTasks):
    """
    启动与小智AI的WebSocket连接

    这个接口会：
    1. 检查设备是否已激活
    2. 初始化WebSocket客户端
    3. 建立连接并进行设备认证
    4. 在后台维持连接

    Returns:
        WebSocketResponse: 操作结果
    """
    try:
        logger.info("🚀 开始启动WebSocket连接")

        # 初始化设备管理器
        initialize_device_managers()

        # 检查设备激活状态
        if not _device_manager.check_activation_status():
            logger.warning("设备未激活，无法建立WebSocket连接")
            return WebSocketResponse(
                success=False,
                message="设备未激活，请先完成设备激活流程",
                data={"activated": False}
            )

        # 检查当前连接状态
        current_status = await get_connection_status()
        if current_status.get("authenticated", False):
            logger.info("WebSocket连接已存在且已认证")
            return WebSocketResponse(
                success=True,
                message="WebSocket连接已存在",
                data=current_status
            )

        # 在后台任务中启动WebSocket连接
        async def start_connection():
            try:
                success = await initialize_websocket_connection(_device_manager)
                if success:
                    logger.info("✅ WebSocket连接启动成功")
                else:
                    logger.error("❌ WebSocket连接启动失败")
            except Exception as e:
                logger.error(f"WebSocket连接启动异常: {e}")

        # 立即尝试连接
        success = await initialize_websocket_connection(_device_manager)

        if success:
            return WebSocketResponse(
                success=True,
                message="WebSocket连接启动成功",
                data=await get_connection_status()
            )
        else:
            return WebSocketResponse(
                success=False,
                message="WebSocket连接启动失败，请检查网络连接和设备状态",
                data=await get_connection_status()
            )

    except Exception as e:
        error_msg = f"启动WebSocket连接时发生错误: {e}"
        logger.error(error_msg)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.post("/stop", response_model=WebSocketResponse)
async def stop_websocket_connection():
    """
    停止WebSocket连接

    Returns:
        WebSocketResponse: 操作结果
    """
    try:
        logger.info("🛑 开始停止WebSocket连接")

        # 获取WebSocket客户端
        client = await get_websocket_client()

        if client.state == ConnectionState.DISCONNECTED:
            return WebSocketResponse(
                success=True,
                message="WebSocket连接已经断开",
                data=await get_connection_status()
            )

        # 断开连接
        await client.disconnect()

        return WebSocketResponse(
            success=True,
            message="WebSocket连接已停止",
            data=await get_connection_status()
        )

    except Exception as e:
        error_msg = f"停止WebSocket连接时发生错误: {e}"
        logger.error(error_msg)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.get("/status", response_model=WebSocketStatusResponse)
async def get_websocket_status():
    """
    获取WebSocket连接状态

    Returns:
        WebSocketStatusResponse: 连接状态信息
    """
    try:
        status = await get_connection_status()

        return WebSocketStatusResponse(
            success=True,
            data=status
        )

    except Exception as e:
        error_msg = f"获取WebSocket状态时发生错误: {e}"
        logger.error(error_msg)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": {"error": error_msg}
            }
        )


@router.post("/reconnect", response_model=WebSocketResponse)
async def reconnect_websocket():
    """
    重新连接WebSocket

    Returns:
        WebSocketResponse: 操作结果
    """
    try:
        logger.info("🔄 开始重新连接WebSocket")

        # 先断开现有连接
        client = await get_websocket_client()
        if client.state != ConnectionState.DISCONNECTED:
            await client.disconnect()
            # 等待一下确保连接完全断开
            await asyncio.sleep(1)

        # 重新建立连接
        initialize_device_managers()
        success = await initialize_websocket_connection(_device_manager)

        if success:
            return WebSocketResponse(
                success=True,
                message="WebSocket重连成功",
                data=await get_connection_status()
            )
        else:
            return WebSocketResponse(
                success=False,
                message="WebSocket重连失败",
                data=await get_connection_status()
            )

    except Exception as e:
        error_msg = f"重连WebSocket时发生错误: {e}"
        logger.error(error_msg)

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": error_msg,
                "data": {}
            }
        )


@router.get("/health")
async def websocket_health_check():
    """
    WebSocket健康检查

    Returns:
        Dict: 健康状态信息
    """
    try:
        status = await get_connection_status()

        # 判断连接健康状态
        is_healthy = status.get("authenticated", False)

        health_info = {
            "healthy": is_healthy,
            "connection_state": status.get("state", "unknown"),
            "connected": status.get("connected", False),
            "authenticated": status.get("authenticated", False),
            "uptime": status.get("stats", {}).get("uptime"),
            "reconnect_attempts": status.get("reconnect_attempts", 0)
        }

        if is_healthy:
            health_info["message"] = "WebSocket连接健康"
        else:
            health_info["message"] = "WebSocket连接不健康"

        return health_info

    except Exception as e:
        logger.error(f"WebSocket健康检查异常: {e}")
        return {
            "healthy": False,
            "message": f"健康检查失败: {e}",
            "connection_state": "error"
        }


@router.get("/stats")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息

    Returns:
        Dict: 统计信息
    """
    try:
        status = await get_connection_status()
        stats = status.get("stats", {})

        return {
            "success": True,
            "data": {
                "connection_stats": stats,
                "current_state": status.get("state"),
                "device_info": status.get("device_info"),
                "config": status.get("config")
            }
        }

    except Exception as e:
        error_msg = f"获取WebSocket统计信息时发生错误: {e}"
        logger.error(error_msg)

        return {
            "success": False,
            "error": error_msg,
            "data": {}
        }


# 启动时自动初始化设备管理器
@router.on_event("startup")
async def startup_event():
    """应用启动事件处理"""
    logger.info("WebSocket路由模块启动")
    initialize_device_managers()


# 关闭时清理资源
@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件处理"""
    logger.info("WebSocket路由模块关闭")

    try:
        # 断开WebSocket连接
        client = await get_websocket_client()
        if client.state != ConnectionState.DISCONNECTED:
            await client.disconnect()
            logger.info("WebSocket连接已在应用关闭时断开")
    except Exception as e:
        logger.error(f"关闭WebSocket连接时发生错误: {e}")