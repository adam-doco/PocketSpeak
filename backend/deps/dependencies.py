# -*- coding: utf-8 -*-
"""
依赖项 - PocketSpeak V1.3
用于 FastAPI 路由的依赖注入
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from core.security import verify_token
from models.user_model import User
from services.auth_service import auth_service


# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    获取当前登录用户（依赖注入）

    Args:
        credentials: HTTP Authorization 头

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: Token 无效或用户不存在
    """
    token = credentials.credentials

    try:
        # 验证 Token
        payload = verify_token(token)

        # 从 payload 中获取 user_id
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 中缺少用户信息"
            )

        # 查询用户
        user = auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        return user

    except Exception as e:
        print(f"❌ 认证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    获取当前登录用户（可选）

    如果没有提供 Token 或 Token 无效，返回 None

    Args:
        credentials: HTTP Authorization 头（可选）

    Returns:
        Optional[User]: 当前用户对象，如果未登录则返回 None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("user_id")

        if user_id:
            return auth_service.get_user_by_id(user_id)

    except Exception:
        pass

    return None
