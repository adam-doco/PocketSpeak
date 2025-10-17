# -*- coding: utf-8 -*-
"""
用户档案数据模型 - PocketSpeak V1.2
用于存储用户的学习目标、英语水平、年龄段等基础信息
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class LearningGoal(str, Enum):
    """学习目标枚举"""
    BUSINESS = "business"  # 商务职场英语
    EXAM = "exam"  # 雅思/KET/PET
    DAILY = "daily"  # 日常口语交流
    TRAVEL = "travel"  # 出国旅游
    OTHER = "other"  # 其他


class EnglishLevel(str, Enum):
    """英语水平枚举 - CEFR标准"""
    A1 = "A1"  # 入门 - 能运用最基础的语句
    A2 = "A2"  # 初级 - 能简单交流讨论问题
    B1 = "B1"  # 中级 - 可以轻松应对日常话题
    B2 = "B2"  # 中高 - 全英文输出复杂观点
    C1 = "C1"  # 高级 - 与外国人交流无障碍
    C2 = "C2"  # 专家 - 如母语者般熟练
    UNCERTAIN = "uncertain"  # 不太确定


class AgeGroup(str, Enum):
    """年龄段枚举"""
    AGE_12_20 = "12-20"  # 12-20岁
    AGE_21_30 = "21-30"  # 21-30岁
    AGE_31_40 = "31-40"  # 31-40岁
    AGE_41_50 = "41-50"  # 41-50岁
    AGE_51_PLUS = "51+"  # 51岁以上


class UserProfile(BaseModel):
    """
    用户档案数据模型

    包含用户的基础信息和学习偏好设置
    """
    user_id: str = Field(..., description="用户UUID")
    device_id: str = Field(..., description="设备ID")
    learning_goal: LearningGoal = Field(..., description="学习目标")
    english_level: EnglishLevel = Field(..., description="英语水平")
    age_group: AgeGroup = Field(..., description="年龄段")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_active: datetime = Field(default_factory=datetime.now, description="最后活跃时间")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "device_id": "ABC123DEF456",
                "learning_goal": "daily",
                "english_level": "B1",
                "age_group": "21-30",
                "created_at": "2025-01-17T10:30:00",
                "last_active": "2025-01-17T10:30:00"
            }
        }


class UserProfileCreateRequest(BaseModel):
    """创建用户档案请求模型"""
    user_id: str = Field(..., description="用户UUID")
    device_id: str = Field(..., description="设备ID")
    learning_goal: str = Field(..., description="学习目标")
    english_level: str = Field(..., description="英语水平")
    age_group: str = Field(..., description="年龄段")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "device_id": "ABC123DEF456",
                "learning_goal": "daily",
                "english_level": "B1",
                "age_group": "21-30"
            }
        }


class UserProfileUpdateRequest(BaseModel):
    """更新用户档案请求模型"""
    learning_goal: Optional[str] = Field(None, description="学习目标")
    english_level: Optional[str] = Field(None, description="英语水平")
    age_group: Optional[str] = Field(None, description="年龄段")

    class Config:
        json_schema_extra = {
            "example": {
                "english_level": "B2",
                "learning_goal": "business"
            }
        }


class UserProfileResponse(BaseModel):
    """用户档案响应模型"""
    success: bool
    message: str
    user_profile: Optional[UserProfile] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "用户档案获取成功",
                "user_profile": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "device_id": "ABC123DEF456",
                    "learning_goal": "daily",
                    "english_level": "B1",
                    "age_group": "21-30",
                    "created_at": "2025-01-17T10:30:00",
                    "last_active": "2025-01-17T10:30:00"
                }
            }
        }
