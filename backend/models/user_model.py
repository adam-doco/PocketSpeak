# -*- coding: utf-8 -*-
"""
用户数据模型 - PocketSpeak V1.3
用于用户登录与注册系统
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class EnglishLevel(str, Enum):
    """英语水平枚举 - CEFR 标准"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    UNCERTAIN = "uncertain"


class AgeRange(str, Enum):
    """年龄段枚举"""
    AGE_12_20 = "12-20"
    AGE_21_30 = "21-30"
    AGE_31_40 = "31-40"
    AGE_41_50 = "41-50"
    AGE_51_PLUS = "51+"


class LoginType(str, Enum):
    """登录方式枚举"""
    EMAIL_CODE = "email_code"  # 邮箱验证码
    APPLE = "apple"  # Apple ID
    PHONE_CODE = "phone_code"  # 手机验证码 (预留)
    WECHAT = "wechat"  # 微信登录 (预留)
    GOOGLE = "google"  # Google 登录 (预留)


class User(BaseModel):
    """
    用户数据模型 - V1.3 统一用户模型

    整合了 V1.2 的用户档案数据和 V1.3 的认证信息
    """
    # 基础信息
    user_id: str = Field(..., description="用户UUID")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    email_verified: bool = Field(default=False, description="邮箱是否验证")

    # 登录信息
    login_type: Optional[LoginType] = Field(None, description="登录方式")
    apple_id: Optional[str] = Field(None, description="Apple ID")

    # V1.2 用户档案信息
    device_id: Optional[str] = Field(None, description="设备ID")
    english_level: Optional[EnglishLevel] = Field(None, description="英语水平")
    age_range: Optional[AgeRange] = Field(None, description="年龄段")
    purpose: Optional[str] = Field(None, description="学英语目的")

    # V1.4 用户个人信息
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="用户头像URL")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    # 扩展字段 (预留)
    phone: Optional[str] = Field(None, description="手机号")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    google_id: Optional[str] = Field(None, description="Google ID")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "email_verified": True,
                "login_type": "email_code",
                "english_level": "B1",
                "age_range": "21-30",
                "purpose": "日常口语交流",
                "created_at": "2025-01-17T10:00:00",
                "updated_at": "2025-01-17T10:00:00",
                "last_login_at": "2025-01-17T10:00:00"
            }
        }


class UserCreate(BaseModel):
    """创建用户请求模型"""
    email: EmailStr
    login_type: LoginType = LoginType.EMAIL_CODE

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "login_type": "email_code"
            }
        }


class UserUpdate(BaseModel):
    """更新用户信息请求模型"""
    english_level: Optional[str] = None
    age_range: Optional[str] = None
    purpose: Optional[str] = None
    device_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "english_level": "B1",
                "age_range": "21-30",
                "purpose": "日常口语交流"
            }
        }


class UserResponse(BaseModel):
    """用户信息响应模型"""
    user_id: str
    email: Optional[str] = None
    email_verified: bool = False
    login_type: Optional[str] = None
    english_level: Optional[str] = None
    age_range: Optional[str] = None
    purpose: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "email_verified": True,
                "login_type": "email_code",
                "english_level": "B1",
                "age_range": "21-30",
                "purpose": "日常口语交流",
                "created_at": "2025-01-17T10:00:00",
                "last_login_at": "2025-01-17T10:00:00"
            }
        }
