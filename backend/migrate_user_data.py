#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据迁移脚本 - V1.2 到 V1.3
将 user_profiles.json 的数据合并到 users.json，统一用户数据存储
"""

import json
from pathlib import Path
from datetime import datetime

def migrate_user_data():
    """迁移用户数据"""
    backend_dir = Path(__file__).parent
    data_dir = backend_dir / "data"

    users_file = data_dir / "users.json"
    profiles_file = data_dir / "user_profiles.json"

    # 检查文件是否存在
    if not profiles_file.exists():
        print("ℹ️  user_profiles.json 不存在，无需迁移")
        return

    if not users_file.exists():
        print("⚠️  users.json 不存在，创建新文件")
        users_file.write_text("{}")

    # 加载数据
    print("\n📂 正在加载数据文件...")
    users = json.loads(users_file.read_text(encoding='utf-8'))
    profiles = json.loads(profiles_file.read_text(encoding='utf-8'))

    print(f"📊 users.json 中有 {len(users)} 个用户")
    print(f"📊 user_profiles.json 中有 {len(profiles)} 个档案")

    # 合并数据
    print("\n🔄 开始合并数据...")
    merged_count = 0
    new_count = 0

    for user_id, profile_data in profiles.items():
        if user_id in users:
            # 用户已存在，更新档案信息
            print(f"  ℹ️  更新用户档案: {user_id}")
            users[user_id].update({
                'device_id': profile_data.get('device_id'),
                'english_level': profile_data.get('english_level'),
                'age_range': profile_data.get('age_group'),  # V1.2: age_group → V1.3: age_range
                'purpose': profile_data.get('learning_goal'),  # V1.2: learning_goal → V1.3: purpose
                'updated_at': datetime.now().isoformat()
            })
            merged_count += 1
        else:
            # 新用户，创建完整数据
            print(f"  ➕ 创建新用户: {user_id}")
            users[user_id] = {
                "user_id": user_id,
                "email": None,
                "email_verified": False,
                "login_type": None,
                "device_id": profile_data.get('device_id'),
                "english_level": profile_data.get('english_level'),
                "age_range": profile_data.get('age_group'),
                "purpose": profile_data.get('learning_goal'),
                "created_at": profile_data.get('created_at'),
                "updated_at": datetime.now().isoformat(),
                "last_login_at": profile_data.get('last_active')
            }
            new_count += 1

    # 保存合并后的数据
    print(f"\n💾 保存合并后的数据到 users.json...")
    users_file.write_text(
        json.dumps(users, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    # 备份并删除旧文件
    backup_file = data_dir / f"user_profiles.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n📦 备份 user_profiles.json 到 {backup_file.name}")
    profiles_file.rename(backup_file)

    # 总结
    print("\n" + "=" * 60)
    print("✅ 数据迁移完成！")
    print("=" * 60)
    print(f"  合并更新: {merged_count} 个用户")
    print(f"  新增用户: {new_count} 个用户")
    print(f"  总用户数: {len(users)} 个")
    print(f"  旧文件已备份: {backup_file.name}")
    print("=" * 60)
    print("\n现在 V1.2 和 V1.3 的用户数据已统一存储在 users.json 中")

if __name__ == "__main__":
    migrate_user_data()
