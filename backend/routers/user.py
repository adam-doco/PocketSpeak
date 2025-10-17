# -*- coding: utf-8 -*-
"""
用户管理 API 路由 - PocketSpeak V1.2
提供用户档案的创建、更新、查询等接口
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from models.user_profile import (
    UserProfile,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
    UserProfileResponse,
    LearningGoal,
    EnglishLevel,
    AgeGroup
)
from services.user_storage_service import user_storage_service


# 创建路由器
router = APIRouter(prefix="/api/user", tags=["user"])


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
