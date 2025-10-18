# -*- coding: utf-8 -*-
"""
V1.4 API 简单测试
使用已登录用户测试 V1.4 新接口
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*60)
print("🧪 V1.4 API 简单测试")
print("="*60)

print("\n📝 测试说明:")
print("   请确保后端服务器正在运行（http://127.0.0.1:8000）")
print("   并且您已经通过邮箱登录注册过至少一个用户")
print("   您需要提供该用户的 Token 来进行测试\n")

# 用户输入 Token
token = input("请输入您的 Bearer Token (从登录接口获取): ").strip()

if not token:
    print("❌ Token 不能为空！")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 1. 测试 GET /api/user/info
print("\n1️⃣  测试 GET /api/user/info...")
try:
    response = requests.get(f"{BASE_URL}/api/user/info", headers=headers)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 用户信息获取成功:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 失败: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 2. 测试 GET /api/user/stats/today
print("\n2️⃣  测试 GET /api/user/stats/today...")
try:
    response = requests.get(f"{BASE_URL}/api/user/stats/today", headers=headers)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 学习统计获取成功:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 失败: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 3. 测试 GET /api/user/settings
print("\n3️⃣  测试 GET /api/user/settings...")
try:
    response = requests.get(f"{BASE_URL}/api/user/settings", headers=headers)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 用户设置获取成功:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 失败: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 4. 测试 POST /api/user/logout
print("\n4️⃣  测试 POST /api/user/logout...")
confirm = input("确认要退出登录吗？ (y/n): ").strip().lower()
if confirm == 'y':
    try:
        response = requests.post(f"{BASE_URL}/api/user/logout", headers=headers)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 退出登录成功:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
else:
    print("⏭️  跳过退出登录测试")

print("\n" + "="*60)
print("✅ V1.4 API 测试完成")
print("="*60 + "\n")
