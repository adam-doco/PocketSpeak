# PocketSpeak 语音交互API使用说明

## 📋 概述

PocketSpeak语音交互系统提供完整的REST API接口，支持语音录制、AI响应、TTS播放和对话历史管理。

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 确保设备已激活

语音会话需要设备先完成激活流程，请确保 `data/device_info.json` 中 `activated: true`。

### 3. 初始化语音会话

```bash
curl -X POST http://localhost:8000/api/voice/session/init \
  -H "Content-Type: application/json" \
  -d '{
    "auto_play_tts": true,
    "save_conversation": true,
    "enable_echo_cancellation": true
  }'
```

## 📡 API端点说明

### 会话管理

#### 初始化语音会话
```
POST /api/voice/session/init
```

**请求体**:
```json
{
  "auto_play_tts": true,
  "save_conversation": true,
  "enable_echo_cancellation": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "语音会话初始化成功",
  "data": {
    "session_id": "session_1234567890",
    "state": "ready",
    "websocket_connected": "authenticated"
  }
}
```

#### 关闭语音会话
```
POST /api/voice/session/close
```

#### 获取会话状态
```
GET /api/voice/session/status
```

### 录音控制

#### 开始录音
```
POST /api/voice/recording/start
```

**功能**: 开始录音并实时发送到AI

#### 停止录音
```
POST /api/voice/recording/stop
```

**功能**: 停止录音，等待AI响应

### 文本交互

#### 发送文本消息
```
POST /api/voice/message/send
```

**请求体**:
```json
{
  "text": "Hello, how are you?"
}
```

### 对话历史

#### 获取对话历史
```
GET /api/voice/conversation/history?limit=50
```

**响应**:
```json
{
  "success": true,
  "message": "获取到 10 条历史消息",
  "data": {
    "messages": [
      {
        "message_id": "msg_1234567890",
        "timestamp": "2025-10-01T10:30:00",
        "user_text": "Hello",
        "ai_text": "Hi, how can I help you?",
        "has_audio": true,
        "message_type": "mcp"
      }
    ],
    "total_count": 10
  }
}
```

### 健康检查

#### 系统健康状态
```
GET /api/voice/health
```

## 🔄 完整交互流程示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 初始化会话
response = requests.post(f"{BASE_URL}/api/voice/session/init", json={
    "auto_play_tts": True,
    "save_conversation": True
})
print(response.json())

# 2. 发送文本消息
response = requests.post(f"{BASE_URL}/api/voice/message/send", json={
    "text": "Tell me a joke"
})
print(response.json())

# 3. 等待AI响应（实际应该通过WebSocket或轮询）
import time
time.sleep(3)

# 4. 获取对话历史
response = requests.get(f"{BASE_URL}/api/voice/conversation/history")
print(response.json())

# 5. 关闭会话
response = requests.post(f"{BASE_URL}/api/voice/session/close")
print(response.json())
```

### JavaScript/TypeScript示例

```javascript
const BASE_URL = "http://localhost:8000";

// 初始化会话
async function initSession() {
  const response = await fetch(`${BASE_URL}/api/voice/session/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      auto_play_tts: true,
      save_conversation: true
    })
  });
  return await response.json();
}

// 开始录音
async function startRecording() {
  const response = await fetch(`${BASE_URL}/api/voice/recording/start`, {
    method: 'POST'
  });
  return await response.json();
}

// 停止录音
async function stopRecording() {
  const response = await fetch(`${BASE_URL}/api/voice/recording/stop`, {
    method: 'POST'
  });
  return await response.json();
}

// 获取对话历史
async function getHistory() {
  const response = await fetch(`${BASE_URL}/api/voice/conversation/history`);
  return await response.json();
}
```

### Flutter/Dart示例

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class VoiceApiService {
  static const String baseUrl = "http://localhost:8000";

  // 初始化会话
  Future<Map<String, dynamic>> initSession() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/voice/session/init'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'auto_play_tts': true,
        'save_conversation': true,
      }),
    );
    return jsonDecode(response.body);
  }

  // 开始录音
  Future<Map<String, dynamic>> startRecording() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/voice/recording/start'),
    );
    return jsonDecode(response.body);
  }

  // 停止录音
  Future<Map<String, dynamic>> stopRecording() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/voice/recording/stop'),
    );
    return jsonDecode(response.body);
  }

  // 发送文本消息
  Future<Map<String, dynamic>> sendText(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/voice/message/send'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text}),
    );
    return jsonDecode(response.body);
  }

  // 获取对话历史
  Future<List<dynamic>> getHistory() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/voice/conversation/history'),
    );
    final data = jsonDecode(response.body);
    return data['data']['messages'] as List;
  }

  // 关闭会话
  Future<Map<String, dynamic>> closeSession() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/voice/session/close'),
    );
    return jsonDecode(response.body);
  }
}
```

## 🔌 WebSocket实时通信

### 连接WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/api/voice/ws');

ws.onopen = () => {
  console.log('WebSocket连接已建立');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'ai_response') {
    console.log('收到AI响应:', data.data);
    // 更新UI显示AI文本
    displayAIText(data.data.text);
  } else if (data.type === 'state_change') {
    console.log('状态变更:', data.data.state);
    // 更新UI显示状态
    updateState(data.data.state);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket错误:', error);
};

ws.onclose = () => {
  console.log('WebSocket连接已关闭');
};
```

## 🧪 测试工具

使用提供的测试脚本：

```bash
cd backend
python test_voice_api.py
```

## 📊 会话状态说明

- **idle**: 空闲状态
- **initializing**: 初始化中
- **ready**: 就绪状态，可以开始录音或发送消息
- **listening**: 正在监听用户语音
- **processing**: 正在处理AI响应
- **speaking**: AI正在说话
- **error**: 错误状态
- **closed**: 会话已关闭

## ⚠️ 注意事项

1. **设备激活**: 必须先完成设备激活流程才能初始化语音会话
2. **会话单例**: 同一时间只能有一个活动的语音会话
3. **资源释放**: 使用完毕后应该调用关闭会话接口释放资源
4. **录音设备**: 录音功能需要系统有可用的麦克风设备
5. **网络连接**: 需要保持与小智AI服务器的WebSocket连接

## 🐛 常见问题

### Q: 初始化会话失败，提示"设备未激活"
A: 请先完成设备激活流程，确保 `data/device_info.json` 中 `activated: true`

### Q: 录音开始失败
A: 检查系统是否有可用的麦克风设备，并确保应用有录音权限

### Q: WebSocket连接失败
A: 检查网络连接，确认小智AI服务器地址正确

### Q: 没有收到AI响应
A: 查看后端日志，确认WebSocket连接状态和消息发送情况

## 📚 相关文档

- [语音交互系统实现日志](../claude_workspace/20251001_voice_interaction_system_integration.md)
- [WebSocket连接模块](../claude_workspace/20251001_websocket_connection_module_implementation.md)
- [语音通信模块](../claude_workspace/20251001_task4_voice_communication_module_implementation.md)

## 🔗 API文档

完整的API文档可以在以下地址查看：
```
http://localhost:8000/docs
```

使用Swagger UI进行交互式API测试。
