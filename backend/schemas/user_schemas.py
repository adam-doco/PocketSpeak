# -*- coding: utf-8 -*-
"""
用户相关 API Schemas - V1.4
定义用户信息、学习统计、设置等接口的请求和响应模型
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import date


class UserInfoResponse(BaseModel):
    """
    用户基础信息响应 - GET /api/user/info
    """
    user_id: str = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    email: Optional[str] = Field(None, description="邮箱地址")
    level: Optional[str] = Field(None, description="英语水平等级，如 A1, B1, C2")
    level_label: Optional[str] = Field(None, description="等级中文标签，如 入门、中级、高级")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "u123456",
                "nickname": "Alex",
                "avatar_url": "https://cdn.pocketspeak.ai/avatar/123.jpg",
                "email": "alex@example.com",
                "level": "B1",
                "level_label": "中级"
            }
        }


class UserStatsResponse(BaseModel):
    """
    用户学习统计响应 - GET /api/user/stats/today
    """
    date: str = Field(..., description="日期，格式 YYYY-MM-DD")
    study_minutes: int = Field(default=0, description="今日学习总时长（分钟）")
    free_talk_count: int = Field(default=0, description="自由对话次数")
    sentence_repeat_count: int = Field(default=0, description="句子跟读次数")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-18",
                "study_minutes": 42,
                "free_talk_count": 3,
                "sentence_repeat_count": 5
            }
        }


class UserSettingsResponse(BaseModel):
    """
    用户设置项响应 - GET /api/user/settings
    """
    account_enabled: bool = Field(default=True, description="是否启用账号管理")
    show_terms: bool = Field(default=True, description="是否显示用户协议")
    show_privacy: bool = Field(default=True, description="是否显示隐私政策")
    logout_enabled: bool = Field(default=True, description="是否启用退出登录")

    class Config:
        json_schema_extra = {
            "example": {
                "account_enabled": True,
                "show_terms": True,
                "show_privacy": True,
                "logout_enabled": True
            }
        }


class LogoutResponse(BaseModel):
    """
    退出登录响应 - POST /api/user/logout
    """
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="退出登录成功", description="响应消息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "退出登录成功"
            }
        }
