# -*- coding: utf-8 -*-
"""
认证路由 - PocketSpeak V1.3
用户登录、注册相关 API 接口
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Dict

from services.auth_service import auth_service


# 创建路由器
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ============== 请求/响应模型 ==============

class SendCodeRequest(BaseModel):
    """发送验证码请求模型"""
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class SendCodeResponse(BaseModel):
    """发送验证码响应模型"""
    success: bool
    message: str
    expires_in: int = 300  # 有效期（秒）

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "验证码已发送",
                "expires_in": 300
            }
        }


class LoginCodeRequest(BaseModel):
    """邮箱验证码登录请求模型"""
    email: EmailStr
    code: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "code": "123456"
            }
        }


class LoginCodeResponse(BaseModel):
    """邮箱验证码登录响应模型"""
    success: bool
    token: str
    user: Dict

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "email_verified": True,
                    "english_level": "B1"
                }
            }
        }


class LoginAppleRequest(BaseModel):
    """Apple 登录请求模型（预留）"""
    apple_id_token: str
    apple_user_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "apple_id_token": "xxx.yyy.zzz",
                "apple_user_id": "001234.xxx"
            }
        }


# ============== API 路由 ==============

@router.post("/send-code", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest):
    """
    发送邮箱验证码

    Args:
        request: 发送验证码请求

    Returns:
        SendCodeResponse: 发送结果

    Raises:
        HTTPException: 发送失败
    """
    print(f"\n📨 收到发送验证码请求: {request.email}")

    result = auth_service.send_code(request.email)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS if "频繁" in result["message"] else status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return SendCodeResponse(
        success=result["success"],
        message=result["message"],
        expires_in=result.get("expires_in", 300)
    )


@router.post("/login-code", response_model=LoginCodeResponse)
async def login_with_email_code(request: LoginCodeRequest):
    """
    邮箱验证码登录

    Args:
        request: 登录请求

    Returns:
        LoginCodeResponse: 登录结果（包含 token 和用户信息）

    Raises:
        HTTPException: 登录失败
    """
    print(f"\n🔐 收到登录请求: {request.email}")

    result = auth_service.login_with_email_code(request.email, request.code)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    print(f"✅ 登录成功: {request.email}")

    return LoginCodeResponse(
        success=result["success"],
        token=result["token"],
        user=result["user"]
    )


@router.post("/login-apple")
async def login_with_apple(request: LoginAppleRequest):
    """
    Apple ID 登录（预留）

    Args:
        request: Apple 登录请求

    Returns:
        Dict: 登录结果

    Raises:
        HTTPException: 501 - 功能未实现
    """
    print(f"\n🍎 收到 Apple 登录请求")

    # TODO: 实现 Apple ID 登录逻辑
    # 1. 验证 Apple ID Token
    # 2. 提取用户信息
    # 3. 查询或创建用户
    # 4. 生成 JWT Token
    # 5. 返回结果

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Apple 登录功能暂未实现"
    )


@router.post("/logout")
async def logout():
    """
    用户登出

    Returns:
        Dict: 登出结果

    Note:
        JWT 是无状态的，登出主要在前端清除 Token
        后端可以实现黑名单机制（预留）
    """
    print(f"\n👋 收到登出请求")

    # TODO: 实现 Token 黑名单机制（可选）

    return {
        "success": True,
        "message": "登出成功"
    }
