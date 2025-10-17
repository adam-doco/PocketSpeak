# -*- coding: utf-8 -*-
"""
用户数据存储服务 - PocketSpeak V1.2
提供用户档案的本地 JSON 文件存储和管理
"""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from models.user_profile import UserProfile, LearningGoal, EnglishLevel, AgeGroup


class UserStorageService:
    """
    用户数据存储服务

    使用 JSON 文件存储用户档案数据
    文件路径：backend/data/user_profiles.json
    """

    def __init__(self, storage_file: Optional[Path] = None):
        """
        初始化用户存储服务

        Args:
            storage_file: 存储文件路径，默认为 backend/data/user_profiles.json
        """
        if storage_file is None:
            # 默认存储在 backend/data/user_profiles.json
            backend_dir = Path(__file__).parent.parent
            data_dir = backend_dir / "data"
            data_dir.mkdir(exist_ok=True)
            storage_file = data_dir / "user_profiles.json"

        self.storage_file = storage_file
        self._ensure_storage_file()

    def _ensure_storage_file(self):
        """确保存储文件存在"""
        if not self.storage_file.exists():
            self.storage_file.write_text(json.dumps({}, indent=2, ensure_ascii=False))
            print(f"✅ 创建用户档案存储文件: {self.storage_file}")

    def _load_all_profiles(self) -> Dict[str, dict]:
        """
        加载所有用户档案

        Returns:
            Dict[str, dict]: 用户ID -> 用户档案字典
        """
        try:
            content = self.storage_file.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"❌ 加载用户档案失败: {e}")
            return {}

    def _save_all_profiles(self, profiles: Dict[str, dict]) -> bool:
        """
        保存所有用户档案

        Args:
            profiles: 用户ID -> 用户档案字典

        Returns:
            bool: 保存是否成功
        """
        try:
            self.storage_file.write_text(
                json.dumps(profiles, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"❌ 保存用户档案失败: {e}")
            return False

    def create_user_profile(self, user_profile: UserProfile) -> bool:
        """
        创建新用户档案

        Args:
            user_profile: 用户档案对象

        Returns:
            bool: 创建是否成功
        """
        try:
            profiles = self._load_all_profiles()

            # 检查用户是否已存在
            if user_profile.user_id in profiles:
                print(f"⚠️ 用户已存在: {user_profile.user_id}")
                return False

            # 保存用户档案
            profiles[user_profile.user_id] = user_profile.model_dump(mode='json')
            success = self._save_all_profiles(profiles)

            if success:
                print(f"✅ 用户档案创建成功: {user_profile.user_id}")
            return success

        except Exception as e:
            print(f"❌ 创建用户档案失败: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户档案

        Args:
            user_id: 用户UUID

        Returns:
            Optional[UserProfile]: 用户档案对象，如果不存在则返回 None
        """
        try:
            profiles = self._load_all_profiles()

            if user_id not in profiles:
                print(f"⚠️ 用户不存在: {user_id}")
                return None

            profile_data = profiles[user_id]

            # 转换为 UserProfile 对象
            user_profile = UserProfile(
                user_id=profile_data["user_id"],
                device_id=profile_data["device_id"],
                learning_goal=LearningGoal(profile_data["learning_goal"]),
                english_level=EnglishLevel(profile_data["english_level"]),
                age_group=AgeGroup(profile_data["age_group"]),
                created_at=datetime.fromisoformat(profile_data["created_at"]),
                last_active=datetime.fromisoformat(profile_data["last_active"])
            )

            return user_profile

        except Exception as e:
            print(f"❌ 获取用户档案失败: {e}")
            return None

    def update_user_profile(
        self,
        user_id: str,
        learning_goal: Optional[str] = None,
        english_level: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> bool:
        """
        更新用户档案

        Args:
            user_id: 用户UUID
            learning_goal: 学习目标（可选）
            english_level: 英语水平（可选）
            age_group: 年龄段（可选）

        Returns:
            bool: 更新是否成功
        """
        try:
            profiles = self._load_all_profiles()

            if user_id not in profiles:
                print(f"⚠️ 用户不存在: {user_id}")
                return False

            profile = profiles[user_id]

            # 更新字段
            if learning_goal is not None:
                # 验证枚举值
                try:
                    LearningGoal(learning_goal)
                    profile["learning_goal"] = learning_goal
                except ValueError:
                    print(f"❌ 无效的学习目标: {learning_goal}")
                    return False

            if english_level is not None:
                try:
                    EnglishLevel(english_level)
                    profile["english_level"] = english_level
                except ValueError:
                    print(f"❌ 无效的英语水平: {english_level}")
                    return False

            if age_group is not None:
                try:
                    AgeGroup(age_group)
                    profile["age_group"] = age_group
                except ValueError:
                    print(f"❌ 无效的年龄段: {age_group}")
                    return False

            # 更新最后活跃时间
            profile["last_active"] = datetime.now().isoformat()

            # 保存更新
            profiles[user_id] = profile
            success = self._save_all_profiles(profiles)

            if success:
                print(f"✅ 用户档案更新成功: {user_id}")
            return success

        except Exception as e:
            print(f"❌ 更新用户档案失败: {e}")
            return False

    def update_last_active(self, user_id: str) -> bool:
        """
        更新用户最后活跃时间

        Args:
            user_id: 用户UUID

        Returns:
            bool: 更新是否成功
        """
        try:
            profiles = self._load_all_profiles()

            if user_id not in profiles:
                return False

            profiles[user_id]["last_active"] = datetime.now().isoformat()
            return self._save_all_profiles(profiles)

        except Exception as e:
            print(f"❌ 更新最后活跃时间失败: {e}")
            return False

    def delete_user_profile(self, user_id: str) -> bool:
        """
        删除用户档案

        Args:
            user_id: 用户UUID

        Returns:
            bool: 删除是否成功
        """
        try:
            profiles = self._load_all_profiles()

            if user_id not in profiles:
                print(f"⚠️ 用户不存在: {user_id}")
                return False

            del profiles[user_id]
            success = self._save_all_profiles(profiles)

            if success:
                print(f"✅ 用户档案删除成功: {user_id}")
            return success

        except Exception as e:
            print(f"❌ 删除用户档案失败: {e}")
            return False

    def get_all_user_ids(self) -> list:
        """
        获取所有用户ID

        Returns:
            list: 用户ID列表
        """
        profiles = self._load_all_profiles()
        return list(profiles.keys())


# 创建全局单例
user_storage_service = UserStorageService()
