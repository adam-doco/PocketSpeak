# -*- coding: utf-8 -*-
"""
V1.3 认证系统 API 测试脚本
测试邮箱验证码登录、JWT Token、获取当前用户等功能
"""

import requests
import time
import json

# 测试配置
BASE_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "test@example.com"

# 全局变量存储 token
token = None


def print_separator(title):
    """打印分割线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_send_code():
    """测试发送验证码"""
    print_separator("测试 1: 发送验证码")

    url = f"{BASE_URL}/api/auth/send-code"
    payload = {"email": TEST_EMAIL}

    print(f"\n📤 POST {url}")
    print(f"📝 请求体: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 200, f"发送验证码失败: {response.text}"
    assert response.json()["success"], "发送验证码返回 success=False"

    print("\n✅ 测试通过: 验证码发送成功")
    return response.json()


def test_send_code_cooldown():
    """测试验证码冷却时间（60秒）"""
    print_separator("测试 2: 验证码冷却机制")

    url = f"{BASE_URL}/api/auth/send-code"
    payload = {"email": TEST_EMAIL}

    print(f"\n📤 POST {url} (第二次发送，应该被拒绝)")
    print(f"📝 请求体: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 429, f"期望 429 Too Many Requests，但得到 {response.status_code}"

    print("\n✅ 测试通过: 冷却机制生效")


def test_login_with_wrong_code():
    """测试错误的验证码"""
    print_separator("测试 3: 错误的验证码")

    url = f"{BASE_URL}/api/auth/login-code"
    payload = {
        "email": TEST_EMAIL,
        "code": "000000"  # 错误的验证码
    }

    print(f"\n📤 POST {url}")
    print(f"📝 请求体: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 400, f"期望 400 Bad Request，但得到 {response.status_code}"

    print("\n✅ 测试通过: 错误验证码被拒绝")


def test_login_with_correct_code(code: str):
    """测试正确的验证码登录"""
    global token

    print_separator("测试 4: 正确的验证码登录")

    url = f"{BASE_URL}/api/auth/login-code"
    payload = {
        "email": TEST_EMAIL,
        "code": code
    }

    print(f"\n📤 POST {url}")
    print(f"📝 请求体: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\n📥 响应状态: {response.status_code}")
    data = response.json()
    print(f"📄 响应内容:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

    assert response.status_code == 200, f"登录失败: {response.text}"
    assert data["success"], "登录返回 success=False"
    assert "token" in data, "响应中没有 token"
    assert "user" in data, "响应中没有 user"

    token = data["token"]

    print(f"\n🔑 获得 Token: {token[:50]}...")
    print("\n✅ 测试通过: 登录成功，获得 Token")

    return data


def test_get_current_user():
    """测试获取当前用户信息"""
    print_separator("测试 5: 获取当前用户信息 (需要认证)")

    url = f"{BASE_URL}/api/user/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"\n📤 GET {url}")
    print(f"🔐 请求头: Authorization: Bearer {token[:50]}...")

    response = requests.get(url, headers=headers)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 200, f"获取用户信息失败: {response.text}"
    data = response.json()
    assert data["success"], "获取用户信息返回 success=False"
    assert "user" in data, "响应中没有 user"
    assert data["user"]["email"] == TEST_EMAIL, "邮箱不匹配"

    print("\n✅ 测试通过: 成功获取当前用户信息")


def test_get_current_user_without_token():
    """测试未携带 Token 访问认证接口"""
    print_separator("测试 6: 未认证访问 /api/user/me")

    url = f"{BASE_URL}/api/user/me"

    print(f"\n📤 GET {url} (不携带 Token)")

    response = requests.get(url)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 403, f"期望 403 Forbidden，但得到 {response.status_code}"

    print("\n✅ 测试通过: 未认证请求被拒绝")


def test_logout():
    """测试登出"""
    print_separator("测试 7: 登出")

    url = f"{BASE_URL}/api/auth/logout"

    print(f"\n📤 POST {url}")

    response = requests.post(url)

    print(f"\n📥 响应状态: {response.status_code}")
    print(f"📄 响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    assert response.status_code == 200, f"登出失败: {response.text}"

    print("\n✅ 测试通过: 登出成功")


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("🧪 " + "=" * 58)
    print("🧪  PocketSpeak V1.3 认证系统 API 测试")
    print("🧪 " + "=" * 58)
    print(f"\n🔗 测试服务器: {BASE_URL}")
    print(f"📧 测试邮箱: {TEST_EMAIL}")

    try:
        # 测试 1: 发送验证码
        test_send_code()

        # 测试 2: 验证冷却机制
        test_send_code_cooldown()

        # 测试 3: 错误的验证码
        test_login_with_wrong_code()

        # 提示用户输入验证码
        print_separator("⏸️  等待输入验证码")
        print(f"\n请查看后端控制台，找到发送给 {TEST_EMAIL} 的验证码")
        code = input("请输入验证码 (6位数字): ").strip()

        # 测试 4: 正确的验证码登录
        test_login_with_correct_code(code)

        # 测试 5: 获取当前用户信息
        test_get_current_user()

        # 测试 6: 未认证访问
        test_get_current_user_without_token()

        # 测试 7: 登出
        test_logout()

        # 所有测试通过
        print("\n")
        print("🎉 " + "=" * 58)
        print("🎉  所有测试通过！")
        print("🎉 " + "=" * 58)

    except AssertionError as e:
        print("\n")
        print("❌ " + "=" * 58)
        print(f"❌  测试失败: {str(e)}")
        print("❌ " + "=" * 58)
        return False

    except Exception as e:
        print("\n")
        print("💥 " + "=" * 58)
        print(f"💥  测试异常: {str(e)}")
        print("💥 " + "=" * 58)
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
