# -*- coding: utf-8 -*-
"""
安全模块 - PocketSpeak V1.3
JWT Token 生成和验证
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
import os


# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24  # Token 有效期 24 小时


def create_access_token(user_id: str, email: str) -> str:
    """
    创建 JWT Access Token

    Args:
        user_id: 用户UUID
        email: 用户邮箱

    Returns:
        str: JWT Token字符串
    """
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    print(f"✅ 为用户 {email} 创建 Token，有效期: {ACCESS_TOKEN_EXPIRE_HOURS}小时")

    return token


def verify_token(token: str) -> Optional[Dict]:
    """
    验证 JWT Token

    Args:
        token: JWT Token字符串

    Returns:
        Optional[Dict]: Token payload，如果无效则返回 None

    Raises:
        Exception: Token 过期或无效
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 验证 token 类型
        if payload.get("type") != "access":
            raise Exception("Token 类型错误")

        return payload

    except jwt.ExpiredSignatureError:
        print("❌ Token 已过期")
        raise Exception("Token 已过期，请重新登录")

    except jwt.JWTError as e:
        print(f"❌ Token 无效: {str(e)}")
        raise Exception("Token 无效，请重新登录")


def decode_token_without_verification(token: str) -> Optional[Dict]:
    """
    解码 Token 但不验证（用于调试）

    Args:
        token: JWT Token字符串

    Returns:
        Optional[Dict]: Token payload
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        print(f"❌ 解码 Token 失败: {str(e)}")
        return None
