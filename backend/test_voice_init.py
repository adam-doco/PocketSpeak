"""
测试语音会话初始化的调试脚本
"""

import setup_paths  # 初始化路径
import asyncio
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from services.device_lifecycle import device_lifecycle_manager, PocketSpeakDeviceManager
from services.voice_chat.voice_session_manager import VoiceSessionManager, SessionConfig

async def test_voice_init():
    """测试语音会话初始化"""
    print("\n" + "="*60)
    print("🧪 开始测试语音会话初始化")
    print("="*60 + "\n")

    # 1. 检查设备激活状态
    print("步骤1: 检查设备激活状态")
    is_activated = device_lifecycle_manager.is_device_activated()
    print(f"   设备激活状态: {'✅ 已激活' if is_activated else '❌ 未激活'}")

    if not is_activated:
        print("\n❌ 设备未激活，无法继续测试")
        return

    # 2. 加载设备信息
    print("\n步骤2: 加载设备信息")
    device_info = device_lifecycle_manager.load_device_info_from_local()
    if device_info:
        print(f"   ✅ 设备信息加载成功")
        print(f"      Device ID: {device_info.device_id}")
        print(f"      Client ID: {device_info.client_id}")
        print(f"      激活方法: {device_info.activation_method}")

        # 检查connection_params
        connection_params = getattr(device_info, 'connection_params', {})
        if connection_params:
            print(f"   ✅ Connection params 存在")
            websocket_params = connection_params.get('websocket', {})
            if websocket_params:
                print(f"      WebSocket URL: {websocket_params.get('url')}")
                print(f"      WebSocket Token: {websocket_params.get('token')}")
            else:
                print(f"   ❌ WebSocket params 不存在")
        else:
            print(f"   ❌ Connection params 不存在")
    else:
        print("   ❌ 设备信息加载失败")
        return

    # 3. 创建设备管理器
    print("\n步骤3: 创建设备管理器")
    device_manager = PocketSpeakDeviceManager(device_lifecycle_manager)
    print("   ✅ 设备管理器创建成功")

    # 4. 创建语音会话管理器
    print("\n步骤4: 创建语音会话管理器")
    session_config = SessionConfig(
        auto_play_tts=True,
        save_conversation=True,
        enable_echo_cancellation=True
    )
    session_manager = VoiceSessionManager(device_manager, session_config)
    print("   ✅ 语音会话管理器创建成功")

    # 5. 初始化会话
    print("\n步骤5: 初始化语音会话")
    try:
        success = await session_manager.initialize()
        if success:
            print("   ✅ 语音会话初始化成功!")

            # 检查状态
            print(f"\n   会话状态:")
            print(f"      Initialized: {session_manager.is_initialized}")
            print(f"      Session ID: {session_manager.session_id}")
            print(f"      State: {session_manager.state.value}")
            print(f"      WebSocket State: {session_manager.ws_client.state.value}")
            print(f"      WebSocket Session ID: {session_manager.ws_client.session_id}")
            print(f"      Is Recording: {session_manager.recorder.is_recording}")
            print(f"      Is Playing: {session_manager.player.is_playing()}")
        else:
            print("   ❌ 语音会话初始化失败")
    except Exception as e:
        print(f"   ❌ 初始化过程出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("🏁 测试完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_voice_init())
