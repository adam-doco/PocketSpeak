# -*- coding: utf-8 -*-
"""
用户管理 API 路由 - PocketSpeak V1.2 & V1.3 & V1.4
提供用户档案的创建、更新、查询等接口
V1.3 新增：GET /api/user/me 获取当前登录用户信息
V1.4 新增：用户信息、学习统计、设置、登出等接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
from datetime import date

from models.user_profile import (
    UserProfile,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
    UserProfileResponse,
    LearningGoal,
    EnglishLevel,
    AgeGroup
)
from models.user_model import User
from services.user_storage_service import user_storage_service
from deps.dependencies import get_current_user
from schemas.user_schemas import (
    UserInfoResponse,
    UserStatsResponse,
    UserSettingsResponse,
    LogoutResponse
)


# 创建路由器
router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> Dict:
    """
    获取当前登录用户信息 - V1.3

    需要认证：Bearer Token

    Args:
        current_user: 当前登录用户（通过 Token 验证）

    Returns:
        Dict: 用户信息

    Raises:
        HTTPException: 401 - 未认证或 Token 无效
    """
    print(f"\n🔍 获取当前用户信息: {current_user.email}")

    return {
        "success": True,
        "user": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "email_verified": current_user.email_verified,
            "login_type": current_user.login_type,
            "device_id": current_user.device_id,
            "english_level": current_user.english_level,
            "age_range": current_user.age_range,
            "purpose": current_user.purpose,
            "created_at": current_user.created_at.isoformat(),
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None
        }
    }


# ==================== V1.4 新增接口（必须在 /{user_id} 之前定义） ====================

@router.get("/info", response_model=UserInfoResponse)
async def get_user_info(current_user: User = Depends(get_current_user)) -> UserInfoResponse:
    """
    获取用户基础信息 - V1.4

    需要认证：Bearer Token

    Returns:
        UserInfoResponse: 用户基础信息（昵称、头像、等级等）
    """
    print(f"\n📋 获取用户信息: {current_user.email}")

    # 等级中文标签映射
    level_labels = {
        "A1": "入门",
        "A2": "初级",
        "B1": "中级",
        "B2": "中高级",
        "C1": "高级",
        "C2": "精通"
    }

    level = current_user.english_level.value if current_user.english_level else None
    level_label = level_labels.get(level) if level else None

    return UserInfoResponse(
        user_id=current_user.user_id,
        nickname=current_user.nickname or current_user.email.split('@')[0] if current_user.email else "用户",
        avatar_url=current_user.avatar_url,
        email=current_user.email,
        level=level,
        level_label=level_label
    )


@router.get("/stats/today", response_model=UserStatsResponse)
async def get_user_stats_today(current_user: User = Depends(get_current_user)) -> UserStatsResponse:
    """
    获取今日学习统计 - V1.4

    需要认证：Bearer Token

    Returns:
        UserStatsResponse: 今日学习统计数据

    Note:
        当前返回 Mock 数据，后续版本接入真实学习记录
    """
    print(f"\n📊 获取今日学习统计: {current_user.email}")

    # TODO: 后续版本从学习记录数据库获取真实数据
    # 当前返回 Mock 数据
    return UserStatsResponse(
        date=str(date.today()),
        study_minutes=0,  # Mock: 今日学习时长
        free_talk_count=0,  # Mock: 自由对话次数
        sentence_repeat_count=0  # Mock: 句子跟读次数
    )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(current_user: User = Depends(get_current_user)) -> UserSettingsResponse:
    """
    获取用户设置项 - V1.4

    需要认证：Bearer Token

    Returns:
        UserSettingsResponse: 设置页面配置项
    """
    print(f"\n⚙️ 获取用户设置: {current_user.email}")

    # 返回设置项配置（支持后期动态开关）
    return UserSettingsResponse(
        account_enabled=True,
        show_terms=True,
        show_privacy=True,
        logout_enabled=True
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(current_user: User = Depends(get_current_user)) -> LogoutResponse:
    """
    用户退出登录 - V1.4

    需要认证：Bearer Token

    Returns:
        LogoutResponse: 退出登录结果

    Note:
        当前实现为客户端主动退出，服务端不维护 Token 黑名单
        客户端需要清除本地存储的 Token
    """
    print(f"\n👋 用户退出登录: {current_user.email}")

    # TODO: 后续版本可以实现 Token 黑名单机制
    # 当前由客户端负责清除 Token

    return LogoutResponse(
        success=True,
        message="退出登录成功"
    )


# ==================== V1.2 用户档案接口 ====================

@router.post("/init", response_model=UserProfileResponse)
async def create_user_profile(request: UserProfileCreateRequest):
    """
    创建用户档案 - V1.2 用户引导流程完成后调用

    Args:
        request: 用户档案创建请求

    Returns:
        UserProfileResponse: 创建结果响应

    Raises:
        HTTPException: 400 - 用户已存在
        HTTPException: 400 - 无效的枚举值
        HTTPException: 500 - 服务器内部错误
    """
    try:
        print(f"\n📝 收到创建用户档案请求: user_id={request.user_id}")

        # 检查用户是否已存在
        existing_profile = user_storage_service.get_user_profile(request.user_id)
        if existing_profile:
            raise HTTPException(
                status_code=400,
                detail=f"用户已存在: {request.user_id}"
            )

        # 验证枚举值
        try:
            learning_goal = LearningGoal(request.learning_goal)
            english_level = EnglishLevel(request.english_level)
            age_group = AgeGroup(request.age_group)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"无效的枚举值: {str(e)}"
            )

        # 创建用户档案对象
        user_profile = UserProfile(
            user_id=request.user_id,
            device_id=request.device_id,
            learning_goal=learning_goal,
            english_level=english_level,
            age_group=age_group
        )

        # 保存到存储
        success = user_storage_service.create_user_profile(user_profile)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="用户档案创建失败"
            )

        print(f"✅ 用户档案创建成功: {request.user_id}")

        return UserProfileResponse(
            success=True,
            message="用户档案创建成功",
            user_profile=user_profile
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 创建用户档案异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建用户档案失败: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """
    获取用户档案

    Args:
        user_id: 用户UUID

    Returns:
        UserProfileResponse: 用户档案响应

    Raises:
        HTTPException: 404 - 用户不存在
        HTTPException: 500 - 服务器内部错误
    """
    try:
        print(f"\n🔍 查询用户档案: user_id={user_id}")

        # 获取用户档案
        user_profile = user_storage_service.get_user_profile(user_id)

        if not user_profile:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在: {user_id}"
            )

        # 更新最后活跃时间
        user_storage_service.update_last_active(user_id)

        print(f"✅ 用户档案查询成功: {user_id}")

        return UserProfileResponse(
            success=True,
            message="用户档案获取成功",
            user_profile=user_profile
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取用户档案异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户档案失败: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(user_id: str, request: UserProfileUpdateRequest):
    """
    更新用户档案

    Args:
        user_id: 用户UUID
        request: 用户档案更新请求

    Returns:
        UserProfileResponse: 更新结果响应

    Raises:
        HTTPException: 404 - 用户不存在
        HTTPException: 400 - 无效的枚举值
        HTTPException: 500 - 服务器内部错误
    """
    try:
        print(f"\n✏️ 更新用户档案: user_id={user_id}")

        # 检查用户是否存在
        existing_profile = user_storage_service.get_user_profile(user_id)
        if not existing_profile:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在: {user_id}"
            )

        # 更新用户档案
        success = user_storage_service.update_user_profile(
            user_id=user_id,
            learning_goal=request.learning_goal,
            english_level=request.english_level,
            age_group=request.age_group
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="用户档案更新失败"
            )

        # 获取更新后的档案
        updated_profile = user_storage_service.get_user_profile(user_id)

        print(f"✅ 用户档案更新成功: {user_id}")

        return UserProfileResponse(
            success=True,
            message="用户档案更新成功",
            user_profile=updated_profile
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 更新用户档案异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新用户档案失败: {str(e)}"
        )


@router.delete("/{user_id}")
async def delete_user_profile(user_id: str) -> Dict:
    """
    删除用户档案（调试用）

    Args:
        user_id: 用户UUID

    Returns:
        Dict: 删除结果

    Raises:
        HTTPException: 404 - 用户不存在
        HTTPException: 500 - 服务器内部错误
    """
    try:
        print(f"\n🗑️ 删除用户档案: user_id={user_id}")

        # 检查用户是否存在
        existing_profile = user_storage_service.get_user_profile(user_id)
        if not existing_profile:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在: {user_id}"
            )

        # 删除用户档案
        success = user_storage_service.delete_user_profile(user_id)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="用户档案删除失败"
            )

        print(f"✅ 用户档案删除成功: {user_id}")

        return {
            "success": True,
            "message": f"用户档案已删除: {user_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 删除用户档案异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除用户档案失败: {str(e)}"
        )


@router.get("/list/all")
async def get_all_users() -> Dict:
    """
    获取所有用户ID列表（调试用）

    Returns:
        Dict: 用户ID列表
    """
    try:
        user_ids = user_storage_service.get_all_user_ids()

        return {
            "success": True,
            "total_users": len(user_ids),
            "user_ids": user_ids,
            "message": "用户列表获取成功"
        }

    except Exception as e:
        print(f"❌ 获取用户列表异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户列表失败: {str(e)}"
        )
