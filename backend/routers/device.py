"""
设备管理相关的API路由
提供设备ID生成、设备信息查询等接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

from core.device_manager import device_manager
from services.bind_verification import start_device_binding, BindingResult
from services.bind_status_listener import wait_for_device_binding, BindStatusResult
from services.zoe_ota_client import zoe_ota_client
from services.zoe_device_manager import zoe_device_manager
# 新的PocketSpeak激活逻辑
from services.device_lifecycle import pocketspeak_device_manager
from services.pocketspeak_activator import pocketspeak_activator


# 创建路由器
router = APIRouter(prefix="/api", tags=["device"])


# 响应模型
class DeviceIdResponse(BaseModel):
    """设备ID响应模型"""
    device_id: str
    status: str = "success"
    message: str = "设备ID生成成功"


class DeviceInfoResponse(BaseModel):
    """设备信息响应模型"""
    device_id: str
    source: str
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    is_activated: bool = False
    additional_info: Optional[Dict] = None
    status: str = "success"
    message: str = "设备信息获取成功"


class BindingRequest(BaseModel):
    """绑定请求模型"""
    timeout: int = 300  # 超时时间，默认5分钟


class BindingResponse(BaseModel):
    """绑定响应模型"""
    success: bool
    verification_code: Optional[str] = None
    message: str = ""
    challenge: Optional[str] = None
    websocket_url: Optional[str] = None
    access_token: Optional[str] = None
    error_detail: Optional[str] = None


class BindStatusRequest(BaseModel):
    """绑定状态轮询请求模型"""
    challenge: str
    timeout: int = 300  # 默认5分钟超时


class BindStatusResponse(BaseModel):
    """绑定状态轮询响应模型"""
    success: bool
    is_activated: bool = False
    websocket_url: Optional[str] = None
    access_token: Optional[str] = None
    message: str = ""
    error_detail: Optional[str] = None


@router.get("/device-id", response_model=DeviceIdResponse)
async def get_device_id():
    """
    获取设备ID

    Returns:
        DeviceIdResponse: 包含设备ID的响应
    """
    try:
        device_id = device_manager.generate_device_id()

        if not device_id:
            raise HTTPException(status_code=500, detail="设备ID生成失败")

        return DeviceIdResponse(
            device_id=device_id,
            status="success",
            message="设备ID生成成功"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成设备ID时发生错误: {str(e)}")


@router.get("/device-info", response_model=DeviceInfoResponse)
async def get_device_info():
    """
    获取完整的设备信息

    Returns:
        DeviceInfoResponse: 包含完整设备信息的响应
    """
    try:
        device_id = device_manager.generate_device_id()
        device_info = device_manager.get_device_info()

        # 获取设备特定信息
        mac_address = device_manager.get_mac_address()
        serial_number = device_manager.get_serial_number()
        is_activated = device_manager.is_activated()

        return DeviceInfoResponse(
            device_id=device_id,
            source=device_info.get("source", "unknown"),
            mac_address=mac_address,
            serial_number=serial_number,
            is_activated=is_activated,
            additional_info=device_info,
            status="success",
            message="设备信息获取成功"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备信息时发生错误: {str(e)}")


@router.post("/device-debug")
async def print_device_debug():
    """
    打印设备调试信息到控制台（开发调试用）

    Returns:
        Dict: 调试信息打印状态
    """
    try:
        device_manager.print_device_debug_info()

        return {
            "status": "success",
            "message": "设备调试信息已输出到控制台"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打印设备调试信息时发生错误: {str(e)}")


@router.post("/device-bind", response_model=BindingResponse)
async def start_device_bind(request: BindingRequest):
    """
    启动设备绑定流程，获取验证码并等待用户绑定确认

    Args:
        request: 绑定请求参数

    Returns:
        BindingResponse: 绑定结果响应
    """
    try:
        # 启动绑定流程
        result = await start_device_binding(timeout=request.timeout)

        # 将绑定结果转换为响应格式
        return BindingResponse(
            success=result.success,
            verification_code=result.verification_code,
            message=result.message,
            challenge=result.challenge,
            websocket_url=result.websocket_url,
            access_token=result.access_token,
            error_detail=result.error_detail
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备绑定流程发生错误: {str(e)}")


@router.get("/device-bind-status")
async def get_device_bind_status():
    """
    获取设备绑定状态

    Returns:
        Dict: 绑定状态信息
    """
    try:
        device_info = device_manager.get_device_info()
        is_activated = device_manager.is_activated()

        return {
            "device_id": device_manager.generate_device_id(),
            "is_activated": is_activated,
            "device_source": device_info.get("source", "unknown"),
            "status": "success",
            "message": "绑定状态查询成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询绑定状态时发生错误: {str(e)}")


@router.post("/device-bind-confirm", response_model=BindStatusResponse)
async def wait_for_bind_confirmation(request: BindStatusRequest):
    """
    等待设备绑定确认，轮询小智AI服务器直到绑定成功

    Args:
        request: 绑定状态轮询请求参数

    Returns:
        BindStatusResponse: 绑定确认结果响应
    """
    try:
        # 启动轮询等待绑定确认
        result = await wait_for_device_binding(
            challenge=request.challenge,
            timeout=request.timeout
        )

        # 将结果转换为响应格式
        return BindStatusResponse(
            success=result.success,
            is_activated=result.is_activated,
            websocket_url=result.websocket_url,
            access_token=result.access_token,
            message=result.message,
            error_detail=result.error_detail
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"绑定确认轮询发生错误: {str(e)}")


class DeviceCodeResponse(BaseModel):
    """设备验证码响应模型"""
    success: bool
    verification_code: Optional[str] = None
    device_id: str = ""
    message: str = ""
    error_detail: Optional[Dict] = None  # 修正类型为Dict
    server_response: Optional[Dict] = None


@router.get("/device/code", response_model=DeviceCodeResponse)
async def get_device_code():
    """
    获取设备绑定验证码 - 使用PocketSpeak真实激活流程（复刻py-xiaozhi）

    Returns:
        DeviceCodeResponse: 包含验证码的响应
    """
    try:
        # 打印设备信息
        pocketspeak_device_manager.print_device_info()

        # 使用PocketSpeak激活器获取验证码
        result = await pocketspeak_activator.request_activation_code()

        return DeviceCodeResponse(
            success=result["success"],
            verification_code=result.get("verification_code"),
            device_id=result.get("device_id", ""),
            message=result.get("message", ""),
            error_detail=result.get("error_detail"),
            server_response=result.get("server_response")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备验证码失败: {str(e)}")


@router.get("/device/zoe-info")
async def get_zoe_device_info():
    """
    获取Zoe风格设备信息

    Returns:
        Dict: Zoe设备身份信息
    """
    try:
        identity = zoe_device_manager.get_or_create_identity()
        return {
            "success": True,
            "device_id": identity["device_id"],
            "client_id": identity["client_id"],
            "serial_number": identity["serial_number"],
            "hmac_key_preview": identity["hmac_key_hex"][:16] + "...",
            "message": "Zoe设备信息获取成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Zoe设备信息失败: {str(e)}")


# 新的PocketSpeak激活流程API端点

class ActivationStatusResponse(BaseModel):
    """激活状态响应模型"""
    is_activated: bool
    device_id: Optional[str] = None
    serial_number: Optional[str] = None
    activation_status: str = ""
    message: str = "激活状态查询成功"


class ActivationConfirmRequest(BaseModel):
    """激活确认请求模型"""
    challenge: str


class ActivationConfirmResponse(BaseModel):
    """激活确认响应模型"""
    success: bool
    message: str = ""
    is_activated: bool = False
    error_detail: Optional[str] = None


@router.get("/device/activation-status", response_model=ActivationStatusResponse)
async def get_activation_status():
    """
    获取设备激活状态 - PocketSpeak真实激活流程

    Returns:
        ActivationStatusResponse: 激活状态信息
    """
    try:
        status_info = await pocketspeak_activator.get_activation_status()

        return ActivationStatusResponse(
            is_activated=status_info["is_activated"],
            device_id=status_info.get("device_id"),
            serial_number=status_info.get("serial_number"),
            activation_status=status_info.get("activation_status", ""),
            message="激活状态查询成功"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询激活状态失败: {str(e)}")


@router.post("/device/confirm-activation", response_model=ActivationConfirmResponse)
async def confirm_activation(request: ActivationConfirmRequest):
    """
    确认设备激活 - 通过HMAC签名验证激活状态

    Args:
        request: 包含挑战字符串的确认请求

    Returns:
        ActivationConfirmResponse: 激活确认结果
    """
    try:
        result = await pocketspeak_activator.confirm_activation(request.challenge)

        return ActivationConfirmResponse(
            success=result["success"],
            message=result.get("message", ""),
            is_activated=result.get("is_activated", False),
            error_detail=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"激活确认失败: {str(e)}")


@router.post("/device/mark-activated")
async def mark_device_activated():
    """
    手动标记设备为已激活 - 用户在xiaozhi.me完成绑定后调用

    Returns:
        Dict: 标记结果
    """
    try:
        success = pocketspeak_activator.manual_mark_activated()

        if success:
            return {
                "success": True,
                "message": "设备已标记为激活状态",
                "is_activated": True
            }
        else:
            return {
                "success": False,
                "message": "标记激活状态失败"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"标记激活状态失败: {str(e)}")


@router.get("/device/pocketspeak-info")
async def get_pocketspeak_device_info():
    """
    获取PocketSpeak设备信息

    Returns:
        Dict: PocketSpeak设备完整信息
    """
    try:
        device_info = pocketspeak_device_manager.get_device_info()
        is_activated = pocketspeak_device_manager.check_activation_status()

        return {
            "success": True,
            "device_id": device_info.get("device_id"),
            "mac_address": device_info.get("mac_address"),
            "serial_number": device_info.get("serial_number"),
            "client_id": device_info.get("client_id"),
            "is_activated": is_activated,
            "activation_status": "已激活" if is_activated else "未激活",
            "hmac_key_preview": device_info.get("hmac_key", "")[:16] + "..." if device_info.get("hmac_key") else "None",
            "message": "PocketSpeak设备信息获取成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取PocketSpeak设备信息失败: {str(e)}")


@router.delete("/device/reset-activation")
async def reset_activation_status():
    """
    重置激活状态为未激活（调试用）

    Returns:
        Dict: 重置结果
    """
    try:
        success = pocketspeak_device_manager.reset_activation_status()

        if success:
            return {
                "success": True,
                "message": "激活状态已重置为未激活",
                "is_activated": False
            }
        else:
            return {
                "success": False,
                "message": "重置激活状态失败"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置激活状态失败: {str(e)}")