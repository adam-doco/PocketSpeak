#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PocketSpeak V1.2 用户 API 测试脚本
测试用户档案的创建、查询、更新、删除功能
"""

import requests
import json
from uuid import uuid4

# API 基础地址
BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """打印测试段落标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_response(response):
    """格式化打印响应"""
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应内容: {response.text}")


def test_create_user_profile():
    """测试创建用户档案"""
    print_section("测试 1: 创建用户档案 - POST /api/user/init")

    user_id = str(uuid4())
    device_id = "TEST_DEVICE_001"

    payload = {
        "user_id": user_id,
        "device_id": device_id,
        "learning_goal": "daily",
        "english_level": "B1",
        "age_group": "21-30"
    }

    print(f"请求参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(f"{BASE_URL}/api/user/init", json=payload)
    print_response(response)

    return user_id


def test_get_user_profile(user_id):
    """测试获取用户档案"""
    print_section("测试 2: 获取用户档案 - GET /api/user/{user_id}")

    print(f"查询用户ID: {user_id}")

    response = requests.get(f"{BASE_URL}/api/user/{user_id}")
    print_response(response)


def test_update_user_profile(user_id):
    """测试更新用户档案"""
    print_section("测试 3: 更新用户档案 - PUT /api/user/{user_id}")

    print(f"更新用户ID: {user_id}")

    payload = {
        "english_level": "B2",
        "learning_goal": "business"
    }

    print(f"更新参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.put(f"{BASE_URL}/api/user/{user_id}", json=payload)
    print_response(response)


def test_get_all_users():
    """测试获取所有用户列表"""
    print_section("测试 4: 获取所有用户列表 - GET /api/user/list/all")

    response = requests.get(f"{BASE_URL}/api/user/list/all")
    print_response(response)


def test_delete_user_profile(user_id):
    """测试删除用户档案"""
    print_section("测试 5: 删除用户档案 - DELETE /api/user/{user_id}")

    print(f"删除用户ID: {user_id}")

    response = requests.delete(f"{BASE_URL}/api/user/{user_id}")
    print_response(response)


def test_invalid_enum_values():
    """测试无效枚举值"""
    print_section("测试 6: 创建用户 - 使用无效枚举值（预期失败）")

    user_id = str(uuid4())

    payload = {
        "user_id": user_id,
        "device_id": "TEST_DEVICE_002",
        "learning_goal": "invalid_goal",  # 无效值
        "english_level": "B1",
        "age_group": "21-30"
    }

    print(f"请求参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(f"{BASE_URL}/api/user/init", json=payload)
    print_response(response)


def test_get_nonexistent_user():
    """测试获取不存在的用户"""
    print_section("测试 7: 获取不存在的用户（预期 404）")

    nonexistent_id = str(uuid4())
    print(f"查询不存在的用户ID: {nonexistent_id}")

    response = requests.get(f"{BASE_URL}/api/user/{nonexistent_id}")
    print_response(response)


def test_duplicate_user_creation(user_id):
    """测试重复创建用户"""
    print_section("测试 8: 重复创建用户（预期失败）")

    payload = {
        "user_id": user_id,
        "device_id": "TEST_DEVICE_003",
        "learning_goal": "exam",
        "english_level": "A2",
        "age_group": "12-20"
    }

    print(f"尝试重复创建用户ID: {user_id}")
    print(f"请求参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(f"{BASE_URL}/api/user/init", json=payload)
    print_response(response)


def main():
    """主测试流程"""
    print("\n" + "🧪" * 30)
    print("  PocketSpeak V1.2 用户 API 测试")
    print("🧪" * 30)

    try:
        # 测试1: 创建用户档案
        user_id = test_create_user_profile()

        # 测试2: 获取用户档案
        test_get_user_profile(user_id)

        # 测试3: 更新用户档案
        test_update_user_profile(user_id)

        # 测试4: 获取所有用户列表
        test_get_all_users()

        # 测试5: 测试无效枚举值
        test_invalid_enum_values()

        # 测试6: 测试获取不存在的用户
        test_get_nonexistent_user()

        # 测试7: 测试重复创建用户
        test_duplicate_user_creation(user_id)

        # 测试8: 删除用户档案
        test_delete_user_profile(user_id)

        print("\n" + "✅" * 30)
        print("  所有测试完成！")
        print("✅" * 30 + "\n")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
