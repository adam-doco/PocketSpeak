#!/usr/bin/env python3
"""
WebSocket API测试脚本
测试PocketSpeak WebSocket生命周期管理API
"""

import requests
import json
import sys

def test_websocket_apis():
    """测试WebSocket API接口"""
    base_url = "http://localhost:8000"

    print("🧪 开始测试PocketSpeak WebSocket API")
    print("=" * 60)

    # 测试1: 健康检查
    print("\n📋 测试1: 服务器健康检查")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ 健康检查: {response.status_code}")
        print(f"📄 响应: {response.json()}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

    # 测试2: WebSocket状态
    print("\n📋 测试2: WebSocket连接状态")
    try:
        response = requests.get(f"{base_url}/api/ws/status", timeout=10)
        print(f"✅ WebSocket状态: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 响应: {response.json()}")
        else:
            print(f"❌ 响应错误: {response.text}")
    except Exception as e:
        print(f"❌ WebSocket状态检查失败: {e}")

    # 测试3: WebSocket健康检查
    print("\n📋 测试3: WebSocket健康检查")
    try:
        response = requests.get(f"{base_url}/api/ws/health", timeout=10)
        print(f"✅ WebSocket健康检查: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 响应: {response.json()}")
        else:
            print(f"❌ 响应错误: {response.text}")
    except Exception as e:
        print(f"❌ WebSocket健康检查失败: {e}")

    # 测试4: WebSocket统计信息
    print("\n📋 测试4: WebSocket统计信息")
    try:
        response = requests.get(f"{base_url}/api/ws/stats", timeout=10)
        print(f"✅ WebSocket统计: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 响应: {response.json()}")
        else:
            print(f"❌ 响应错误: {response.text}")
    except Exception as e:
        print(f"❌ WebSocket统计信息失败: {e}")

    # 测试5: 启动WebSocket连接（预期失败，因为设备未激活）
    print("\n📋 测试5: 启动WebSocket连接")
    try:
        response = requests.post(f"{base_url}/api/ws/start", timeout=15)
        print(f"✅ WebSocket启动请求: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"📄 响应: {result}")
            if not result.get('success'):
                print("🔍 预期结果: 设备未激活，无法启动连接")
        else:
            print(f"❌ 响应错误: {response.text}")
    except Exception as e:
        print(f"❌ WebSocket启动失败: {e}")

    print("\n" + "=" * 60)
    print("🎯 WebSocket API测试完成")
    return True

if __name__ == "__main__":
    test_websocket_apis()