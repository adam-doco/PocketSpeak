# -*- coding: utf-8 -*-
"""
V1.4 API 测试脚本
测试新增的用户信息、学习统计、设置等接口
"""

from fastapi.testclient import TestClient
from main import app
from core.security import create_access_token
from models.user_model import User, LoginType, EnglishLevel, AgeRange
from datetime import datetime

# 创建测试客户端
client = TestClient(app)

print("\n" + "="*60)
print("🧪 V1.4 API 功能测试")
print("="*60)

# 1. 创建测试用户并获取 Token
print("\n1️⃣  创建测试用户并获取 Token...")
from services.auth_service import auth_service

test_email = "test_v1_4@pocketspeak.ai"
test_user_id = "test_user_v1_4_001"

# 注册测试用户
test_user = auth_service.register_user(
    email=test_email,
    login_type=LoginType.EMAIL_CODE
)

# 更新用户信息
auth_service.update_user(test_user.user_id, {
    "english_level": EnglishLevel.B1.value,
    "age_range": AgeRange.AGE_21_30.value,
    "purpose": "测试 V1.4 功能",
    "nickname": "测试用户"
})

# 生成测试 Token
test_token = create_access_token(
    user_id=test_user.user_id,
    email=test_user.email
)
print(f"✅ Token 创建成功: {test_token[:20]}...")

# 设置请求头
headers = {"Authorization": f"Bearer {test_token}"}

# 2. 测试 GET /api/user/info
print("\n2️⃣  测试 GET /api/user/info...")
response = client.get("/api/user/info", headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 用户信息获取成功:")
    print(f"   - user_id: {data['user_id']}")
    print(f"   - nickname: {data['nickname']}")
    print(f"   - email: {data['email']}")
    print(f"   - level: {data['level']}")
    print(f"   - level_label: {data['level_label']}")
else:
    print(f"❌ 失败: {response.json()}")

# 3. 测试 GET /api/user/stats/today
print("\n3️⃣  测试 GET /api/user/stats/today...")
response = client.get("/api/user/stats/today", headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 学习统计获取成功:")
    print(f"   - date: {data['date']}")
    print(f"   - study_minutes: {data['study_minutes']}")
    print(f"   - free_talk_count: {data['free_talk_count']}")
    print(f"   - sentence_repeat_count: {data['sentence_repeat_count']}")
else:
    print(f"❌ 失败: {response.json()}")

# 4. 测试 GET /api/user/settings
print("\n4️⃣  测试 GET /api/user/settings...")
response = client.get("/api/user/settings", headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 用户设置获取成功:")
    print(f"   - account_enabled: {data['account_enabled']}")
    print(f"   - show_terms: {data['show_terms']}")
    print(f"   - show_privacy: {data['show_privacy']}")
    print(f"   - logout_enabled: {data['logout_enabled']}")
else:
    print(f"❌ 失败: {response.json()}")

# 5. 测试 POST /api/user/logout
print("\n5️⃣  测试 POST /api/user/logout...")
response = client.post("/api/user/logout", headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 退出登录成功:")
    print(f"   - success: {data['success']}")
    print(f"   - message: {data['message']}")
else:
    print(f"❌ 失败: {response.json()}")

# 6. 测试未认证访问（应该返回 401）
print("\n6️⃣  测试未认证访问（应返回 401）...")
response = client.get("/api/user/info")
print(f"状态码: {response.status_code}")
if response.status_code == 401:
    print(f"✅ 正确返回 401 未认证错误")
else:
    print(f"❌ 异常: 应返回 401 但返回了 {response.status_code}")

print("\n" + "="*60)
print("✅ V1.4 API 测试完成")
print("="*60 + "\n")

# 清理测试数据
# 注意：手动清理测试用户
print("⚠️  请手动清理测试用户数据")
