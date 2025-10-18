# -*- coding: utf-8 -*-
"""
认证服务 - PocketSpeak V1.3
处理用户登录、注册、验证码等业务逻辑
"""

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from uuid import uuid4

from models.user_model import User, UserCreate, LoginType
from core.security import create_access_token
from utils.email_sender import send_verification_code


class AuthService:
    """认证服务类"""

    def __init__(self):
        """初始化认证服务"""
        # 数据存储路径
        backend_dir = Path(__file__).parent.parent
        self.data_dir = backend_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.users_file = self.data_dir / "users.json"
        self.codes_file = self.data_dir / "verification_codes.json"

        # 确保文件存在
        self._ensure_files()

    def _ensure_files(self):
        """确保数据文件存在"""
        if not self.users_file.exists():
            self.users_file.write_text(json.dumps({}, indent=2, ensure_ascii=False))
            print(f"✅ 创建用户数据文件: {self.users_file}")

        if not self.codes_file.exists():
            self.codes_file.write_text(json.dumps({}, indent=2, ensure_ascii=False))
            print(f"✅ 创建验证码数据文件: {self.codes_file}")

    def _load_users(self) -> Dict:
        """加载用户数据"""
        try:
            return json.loads(self.users_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"❌ 加载用户数据失败: {e}")
            return {}

    def _save_users(self, users: Dict) -> bool:
        """保存用户数据"""
        try:
            self.users_file.write_text(
                json.dumps(users, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"❌ 保存用户数据失败: {e}")
            return False

    def _load_codes(self) -> Dict:
        """加载验证码数据"""
        try:
            return json.loads(self.codes_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"❌ 加载验证码数据失败: {e}")
            return {}

    def _save_codes(self, codes: Dict) -> bool:
        """保存验证码数据"""
        try:
            self.codes_file.write_text(
                json.dumps(codes, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"❌ 保存验证码数据失败: {e}")
            return False

    def generate_verification_code(self) -> str:
        """生成6位随机数字验证码"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def send_code(self, email: str) -> Dict:
        """
        发送验证码

        Args:
            email: 邮箱地址

        Returns:
            Dict: 发送结果
        """
        codes = self._load_codes()

        # 检查冷却时间（60秒）
        if email in codes:
            last_sent = datetime.fromisoformat(codes[email]["created_at"])
            cooldown = timedelta(seconds=60)
            if datetime.now() - last_sent < cooldown:
                remaining = 60 - int((datetime.now() - last_sent).total_seconds())
                return {
                    "success": False,
                    "message": f"发送频繁，请{remaining}秒后再试"
                }

        # 生成验证码
        code = self.generate_verification_code()

        # 保存验证码（有效期5分钟）
        codes[email] = {
            "code": code,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "used": False
        }

        self._save_codes(codes)

        # 发送邮件
        send_success = send_verification_code(email, code)

        if send_success:
            print(f"✅ 验证码已发送到: {email}")
            return {
                "success": True,
                "message": "验证码已发送",
                "expires_in": 300  # 5分钟
            }
        else:
            return {
                "success": False,
                "message": "验证码发送失败，请稍后重试"
            }

    def verify_code(self, email: str, code: str) -> Dict:
        """
        验证验证码

        Args:
            email: 邮箱地址
            code: 验证码

        Returns:
            Dict: 验证结果
        """
        # 万能测试验证码（开发环境）
        if code == "666666":
            print(f"🔓 使用万能测试验证码: {email}")
            return {
                "success": True,
                "message": "验证码正确（测试模式）"
            }

        codes = self._load_codes()

        # 检查验证码是否存在
        if email not in codes:
            return {
                "success": False,
                "message": "验证码不存在或已过期"
            }

        code_data = codes[email]

        # 检查是否已使用
        if code_data.get("used", False):
            return {
                "success": False,
                "message": "验证码已使用"
            }

        # 检查是否过期
        expires_at = datetime.fromisoformat(code_data["expires_at"])
        if datetime.now() > expires_at:
            return {
                "success": False,
                "message": "验证码已过期"
            }

        # 验证验证码
        if code_data["code"] != code:
            return {
                "success": False,
                "message": "验证码错误"
            }

        # 标记为已使用
        codes[email]["used"] = True
        self._save_codes(codes)

        return {
            "success": True,
            "message": "验证码正确"
        }

    def login_with_email_code(self, email: str, code: str) -> Dict:
        """
        邮箱验证码登录

        Args:
            email: 邮箱地址
            code: 验证码

        Returns:
            Dict: 登录结果（包含 token 和用户信息）
        """
        # 1. 验证验证码
        verify_result = self.verify_code(email, code)
        if not verify_result["success"]:
            return verify_result

        # 2. 检查用户是否存在
        users = self._load_users()
        user_id = None
        user_data = None

        # 查找用户
        for uid, udata in users.items():
            if udata.get("email") == email:
                user_id = uid
                user_data = udata
                break

        # 3. 如果用户不存在，创建新用户
        if not user_data:
            print(f"📝 新用户注册: {email}")
            user_id = str(uuid4())
            user_data = {
                "user_id": user_id,
                "email": email,
                "email_verified": True,
                "login_type": LoginType.EMAIL_CODE.value,
                "device_id": None,
                "english_level": None,
                "age_range": None,
                "purpose": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_login_at": datetime.now().isoformat()
            }
            users[user_id] = user_data
        else:
            # 4. 如果用户存在，更新最后登录时间
            print(f"✅ 老用户登录: {email}")
            user_data["last_login_at"] = datetime.now().isoformat()
            user_data["updated_at"] = datetime.now().isoformat()
            users[user_id] = user_data

        self._save_users(users)

        # 5. 生成 JWT Token
        token = create_access_token(user_id, email)

        # 6. 返回结果
        return {
            "success": True,
            "token": token,
            "user": {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "email_verified": user_data.get("email_verified", False),
                "login_type": user_data.get("login_type"),
                "english_level": user_data.get("english_level"),
                "age_range": user_data.get("age_range"),
                "purpose": user_data.get("purpose"),
                "created_at": user_data["created_at"],
                "last_login_at": user_data.get("last_login_at")
            }
        }

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        根据 user_id 获取用户信息

        Args:
            user_id: 用户UUID

        Returns:
            Optional[User]: 用户对象，不存在则返回 None
        """
        users = self._load_users()

        if user_id not in users:
            return None

        user_data = users[user_id]

        try:
            return User(**user_data)
        except Exception as e:
            print(f"❌ 解析用户数据失败: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户信息

        Args:
            email: 邮箱地址

        Returns:
            Optional[User]: 用户对象，不存在则返回 None
        """
        users = self._load_users()

        for user_data in users.values():
            if user_data.get("email") == email:
                try:
                    return User(**user_data)
                except Exception as e:
                    print(f"❌ 解析用户数据失败: {e}")
                    return None

        return None

    def update_user(self, user_id: str, update_data: Dict) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户UUID
            update_data: 更新的数据

        Returns:
            Optional[User]: 更新后的用户对象
        """
        users = self._load_users()

        if user_id not in users:
            return None

        user_data = users[user_id]

        # 更新字段
        for key, value in update_data.items():
            if value is not None:
                user_data[key] = value

        # 更新时间戳
        user_data["updated_at"] = datetime.now().isoformat()

        users[user_id] = user_data
        self._save_users(users)

        try:
            return User(**user_data)
        except Exception as e:
            print(f"❌ 解析用户数据失败: {e}")
            return None


# 创建全局单例
auth_service = AuthService()
