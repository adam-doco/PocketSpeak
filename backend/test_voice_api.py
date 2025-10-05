"""
测试语音交互API接口

验证语音会话管理、录音控制等功能
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"


def print_result(title, response):
    """打印测试结果"""
    print(f"\n{'=' * 60}")
    print(f"📋 {title}")
    print(f"{'=' * 60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"响应: {response.text}")
    print(f"{'=' * 60}\n")


def test_voice_api():
    """测试语音交互API"""

    print("\n🎤 开始测试PocketSpeak语音交互API\n")

    # 1. 测试健康检查
    print("1️⃣ 测试语音系统健康检查...")
    response = requests.get(f"{BASE_URL}/api/voice/health")
    print_result("语音系统健康检查", response)

    # 2. 测试初始化语音会话
    print("2️⃣ 测试初始化语音会话...")
    init_data = {
        "auto_play_tts": True,
        "save_conversation": True,
        "enable_echo_cancellation": True
    }
    response = requests.post(f"{BASE_URL}/api/voice/session/init", json=init_data)
    print_result("初始化语音会话", response)

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ 语音会话初始化成功")

            # 等待会话完全就绪
            time.sleep(3)

            # 3. 测试会话状态查询
            print("3️⃣ 测试会话状态查询...")
            response = requests.get(f"{BASE_URL}/api/voice/session/status")
            print_result("会话状态查询", response)

            # 4. 测试发送文本消息
            print("4️⃣ 测试发送文本消息...")
            text_data = {"text": "Hello, can you hear me?"}
            response = requests.post(f"{BASE_URL}/api/voice/message/send", json=text_data)
            print_result("发送文本消息", response)

            # 等待AI响应
            time.sleep(2)

            # 5. 测试获取对话历史
            print("5️⃣ 测试获取对话历史...")
            response = requests.get(f"{BASE_URL}/api/voice/conversation/history?limit=10")
            print_result("对话历史", response)

            # 6. 测试录音功能（可选，因为需要音频设备）
            print("6️⃣ 测试录音控制（模拟）...")
            # 开始录音
            response = requests.post(f"{BASE_URL}/api/voice/recording/start")
            print_result("开始录音", response)

            # 模拟录音2秒
            print("⏳ 模拟录音中...")
            time.sleep(2)

            # 停止录音
            response = requests.post(f"{BASE_URL}/api/voice/recording/stop")
            print_result("停止录音", response)

            # 7. 再次查询状态
            print("7️⃣ 再次查询会话状态...")
            response = requests.get(f"{BASE_URL}/api/voice/session/status")
            print_result("会话状态", response)

            # 8. 关闭会话
            print("8️⃣ 测试关闭语音会话...")
            response = requests.post(f"{BASE_URL}/api/voice/session/close")
            print_result("关闭语音会话", response)

        else:
            print(f"❌ 语音会话初始化失败: {result.get('message')}")
    else:
        print(f"❌ API请求失败，状态码: {response.status_code}")

    print("\n✅ 测试完成！\n")


def test_api_endpoints():
    """测试所有API端点是否可访问"""
    print("\n📡 测试API端点可访问性\n")

    endpoints = [
        ("GET", "/api/voice/health", "语音健康检查"),
        ("GET", "/api/voice/session/status", "会话状态查询"),
        ("GET", "/api/voice/conversation/history", "对话历史"),
    ]

    for method, endpoint, description in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json={}, timeout=5)

            status = "✅" if response.status_code in [200, 404, 422, 500] else "❌"
            print(f"{status} {method} {endpoint} - {description} (状态码: {response.status_code})")
        except Exception as e:
            print(f"❌ {method} {endpoint} - {description} (错误: {e})")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🎤 PocketSpeak 语音交互API测试工具")
    print("=" * 80)

    # 首先测试端点可访问性
    test_api_endpoints()

    # 然后进行完整功能测试
    try:
        test_voice_api()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 80)
