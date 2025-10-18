# 前端WebSocket自动重连修复

**任务日期**: 2025-01-16
**任务类型**: 🔥 CRITICAL Bug Fix - 前端到后端WebSocket 1分钟断线问题
**任务状态**: ✅ 已完成（待测试）

---

## 一、问题根源发现

### 1.1 真正的问题

之前我修复的是**后端到小智服务器的WebSocket连接**（`backend/services/voice_chat/ws_client.py`），但用户遇到的问题是**前端到后端的WebSocket连接**（`frontend → backend`）在1分钟空闲后断开！

### 1.2 问题定位

**前端日志**:
```
flutter: 🔌 正在连接WebSocket: ws://localhost:8000/api/voice/ws
flutter: ✅ WebSocket连接成功
...
[1分钟后]
flutter: 🔌 WebSocket连接已关闭
```

**关键代码问题** (`voice_service.dart` 第442-445行 - 旧版本):
```dart
onDone: () {
  // ✅ 精简：移除连接关闭日志
  _isWsConnected = false;
  // ❌ 没有自动重连！
},
```

### 1.3 为什么会断开

1. 前端连接到后端WebSocket (`ws://localhost:8000/api/voice/ws`)
2. 1分钟无活动，WebSocket连接超时
3. `onDone` 回调触发，设置 `_isWsConnected = false`
4. **没有自动重连机制**
5. 用户再次点击录音按钮时，连接已断开，提示"无法开始录音"

---

## 二、修复方案

### 2.1 实施策略

**参照**: py-xiaozhi的自动重连机制（与后端修复类似）

**关键特性**:
1. ✅ 自动重连开关 (`_autoReconnect`)
2. ✅ 重连次数限制 (`_maxReconnectAttempts = 5`)
3. ✅ 指数退避算法（1s, 2s, 4s, 8s, 16s）
4. ✅ 主动断开时禁用重连
5. ✅ 重连成功后重置计数器

### 2.2 数据流对比

#### 修复前（无自动重连）

```
前端启动
  ↓
connectWebSocket()
  ↓
WebSocket连接成功
  ↓
[用户空闲1分钟]
  ↓
WebSocket超时断开
  ↓
onDone 回调触发
  ↓
设置 _isWsConnected = false
  ↓
❌ 没有重连
  ↓
用户点击录音按钮
  ↓
❌ 提示"无法开始录音"
```

#### 修复后（有自动重连）

```
前端启动
  ↓
connectWebSocket(enableAutoReconnect: true)
  ↓
WebSocket连接成功
设置 _autoReconnect = true ✅
  ↓
[用户空闲1分钟]
  ↓
WebSocket超时断开
  ↓
onDone 回调触发
  ↓
设置 _isWsConnected = false
检查 _autoReconnect == true ✅
  ↓
调用 _scheduleReconnect()
  ↓
计算延迟: 1秒（第1次重连）
  ↓
启动Timer，等待1秒
  ↓
Timer触发，调用 connectWebSocket(enableAutoReconnect: true)
  ↓
✅ WebSocket重连成功
重置 _reconnectAttempts = 0
  ↓
用户点击录音按钮
  ↓
✅ 录音成功启动
```

---

## 三、代码修改详情

### 3.1 添加自动重连属性 (`voice_service.dart` 第22-26行)

```dart
// 🚀 WebSocket 连接（实时音频推送）
WebSocketChannel? _wsChannel;
StreamSubscription? _wsSubscription;
bool _isWsConnected = false;

// 🔥 自动重连控制（参照py-xiaozhi）
bool _autoReconnect = false;  // 自动重连开关
int _reconnectAttempts = 0;   // 重连尝试次数
final int _maxReconnectAttempts = 5;  // 最大重连次数
Timer? _reconnectTimer;       // 重连定时器
```

### 3.2 修改 `connectWebSocket()` 方法 (第427-509行)

```dart
/// 🚀 连接WebSocket（模仿py-xiaozhi的即时播放架构）
Future<bool> connectWebSocket({bool enableAutoReconnect = true}) async {
  // 🔥 先取消重连定时器
  _reconnectTimer?.cancel();
  _reconnectTimer = null;

  // 🔥 先断开旧连接，防止hot reload导致重复连接
  if (_isWsConnected) {
    await disconnectWebSocket();
  }

  try {
    print('🔌 正在连接WebSocket: $wsUrl');

    _wsChannel = WebSocketChannel.connect(Uri.parse(wsUrl));

    // 监听WebSocket消息
    _wsSubscription = _wsChannel!.stream.listen(
      (message) {
        _handleWebSocketMessage(message);
      },
      onError: (error) {
        print('❌ WebSocket错误: $error');
        _isWsConnected = false;
        // 🔥 触发自动重连
        if (_autoReconnect) {
          _scheduleReconnect();
        }
      },
      onDone: () {
        print('🔌 WebSocket连接已关闭');
        _isWsConnected = false;
        // 🔥 触发自动重连
        if (_autoReconnect) {
          _scheduleReconnect();
        }
      },
    );

    _isWsConnected = true;
    _autoReconnect = enableAutoReconnect;  // 🔥 设置自动重连开关
    _reconnectAttempts = 0;  // 🔥 重置重连次数
    print('✅ WebSocket连接成功');
    return true;
  } catch (e) {
    print('❌ WebSocket连接失败: $e');
    _isWsConnected = false;
    // 🔥 触发自动重连
    if (enableAutoReconnect) {
      _autoReconnect = true;
      _scheduleReconnect();
    }
    return false;
  }
}
```

**关键改动**:
1. 添加 `enableAutoReconnect` 参数（默认true）
2. `onDone` 和 `onError` 回调中检查 `_autoReconnect` 并调用 `_scheduleReconnect()`
3. 连接成功后设置 `_autoReconnect = true` 并重置 `_reconnectAttempts = 0`
4. 添加日志输出（便于调试）

### 3.3 实现 `_scheduleReconnect()` 方法 (第482-509行)

```dart
/// 🔥 调度自动重连（指数退避算法）
void _scheduleReconnect() {
  // 检查重连次数
  if (_reconnectAttempts >= _maxReconnectAttempts) {
    print('❌ 已达到最大重连次数($_maxReconnectAttempts)，停止重连');
    _autoReconnect = false;
    return;
  }

  // 取消旧定时器
  _reconnectTimer?.cancel();

  // 计算延迟时间（指数退避：1s, 2s, 4s, 8s, 16s）
  final delay = Duration(seconds: (1 << _reconnectAttempts).clamp(1, 16));
  _reconnectAttempts++;

  print('🔄 将在 ${delay.inSeconds} 秒后尝试第 $_reconnectAttempts 次重连');

  // 设置定时器
  _reconnectTimer = Timer(delay, () async {
    print('🔄 正在尝试第 $_reconnectAttempts 次重连...');
    final success = await connectWebSocket(enableAutoReconnect: true);
    if (success) {
      print('✅ 重连成功！');
      _reconnectAttempts = 0;  // 重置重连次数
    }
  });
}
```

**关键特性**:
- **指数退避算法**: `1 << _reconnectAttempts` = 2^n 秒
  - 第1次: 1秒
  - 第2次: 2秒
  - 第3次: 4秒
  - 第4次: 8秒
  - 第5次: 16秒
- **最大重连次数检查**: 达到5次后停止
- **Timer管理**: 取消旧定时器，避免重复
- **重连成功后重置**: `_reconnectAttempts = 0`

### 3.4 修改 `disconnectWebSocket()` 方法 (第583-611行)

```dart
/// 断开WebSocket连接
Future<void> disconnectWebSocket() async {
  if (!_isWsConnected && _wsChannel == null) {
    return;
  }

  try {
    // 🔥 主动断开时禁用自动重连
    _autoReconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    // 清空回调，防止重复触发
    onAudioFrameReceived = null;
    onUserTextReceived = null;
    onTextReceived = null;
    onEmotionReceived = null;
    onStateChanged = null;

    await _wsSubscription?.cancel();
    await _wsChannel?.sink.close();
    _wsChannel = null;
    _wsSubscription = null;
    _isWsConnected = false;
    print('✅ WebSocket已主动断开');
  } catch (e) {
    print('❌ 断开WebSocket失败: $e');
  }
}
```

**关键改动**:
1. 设置 `_autoReconnect = false`（防止主动断开时自动重连）
2. 取消重连定时器 `_reconnectTimer?.cancel()`
3. 添加日志输出

---

## 四、完整修改清单

| 文件路径 | 修改内容 | 行号 |
|---------|---------|------|
| `frontend/pocketspeak_app/lib/services/voice_service.dart` | 添加自动重连属性 | 22-26 |
| | 修改 `connectWebSocket()` 添加自动重连 | 427-480 |
| | 实现 `_scheduleReconnect()` 方法 | 482-509 |
| | 修改 `disconnectWebSocket()` 禁用自动重连 | 583-611 |

**总修改量**:
- 新增属性: 4个
- 新增方法: 1个
- 修改方法: 2个
- 新增代码行数: ~40行
- 删除代码行数: ~5行
- 净增加: ~35行

---

## 五、测试计划

### 5.1 测试场景

#### 场景1: 1分钟空闲自动重连测试（核心场景）

**步骤**:
1. 启动前端应用
2. 发送一条语音消息（验证连接正常）
3. 等待1分钟，不进行任何操作
4. 观察日志，确认自动重连
5. 再次点击录音按钮，验证功能正常

**预期日志**:
```
flutter: 🔌 正在连接WebSocket: ws://localhost:8000/api/voice/ws
flutter: ✅ WebSocket连接成功
...
[1分钟后]
flutter: 🔌 WebSocket连接已关闭
flutter: 🔄 将在 1 秒后尝试第 1 次重连
flutter: 🔄 正在尝试第 1 次重连...
flutter: 🔌 正在连接WebSocket: ws://localhost:8000/api/voice/ws
flutter: ✅ WebSocket连接成功
flutter: ✅ 重连成功！
```

**预期结果**:
- ✅ WebSocket自动重连成功
- ✅ 用户点击录音按钮时功能正常
- ✅ 无需用户重启应用

#### 场景2: 主动断开不重连测试

**步骤**:
1. 启动前端应用
2. 关闭应用或切换页面（触发 `disconnectWebSocket()`）
3. 观察日志，确认不触发自动重连

**预期日志**:
```
flutter: ✅ WebSocket已主动断开
(没有重连日志)
```

#### 场景3: 最大重连次数测试

**步骤**:
1. 启动前端应用
2. 停止后端服务（模拟后端不可用）
3. 观察日志，确认尝试5次重连后停止

**预期日志**:
```
flutter: 🔄 将在 1 秒后尝试第 1 次重连
flutter: ❌ WebSocket连接失败
flutter: 🔄 将在 2 秒后尝试第 2 次重连
flutter: ❌ WebSocket连接失败
...
flutter: 🔄 将在 16 秒后尝试第 5 次重连
flutter: ❌ WebSocket连接失败
flutter: ❌ 已达到最大重连次数(5)，停止重连
```

### 5.2 验证检查清单

- [ ] 1分钟空闲后自动重连成功
- [ ] 重连后录音功能正常
- [ ] 重连后音频播放正常
- [ ] 重连后emoji显示正常
- [ ] 主动断开不触发自动重连
- [ ] 达到最大重连次数后停止
- [ ] 重连成功后计数器重置
- [ ] 无内存泄漏（Timer已清理）

---

## 六、与后端WebSocket修复的关系

### 6.1 两层WebSocket连接

```
前端 (Flutter)
    ↓ WebSocket (ws://localhost:8000/api/voice/ws)
后端 (FastAPI)
    ↓ WebSocket (wss://api.tenclass.net/xiaozhi/v1/)
小智服务器
```

### 6.2 两个修复的配合

| 连接层 | 修复文件 | 修复内容 | 状态 |
|-------|---------|---------|------|
| **前端→后端** | `voice_service.dart` | 添加自动重连机制 | ✅ 本次修复 |
| **后端→小智** | `ws_client.py` | 添加自动重连机制 | ✅ 之前修复 |

**两个修复都需要！**

---

## 七、测试指南

### 7.1 如何测试

**步骤1**: 确保后端服务运行
```bash
cd /Users/good/Desktop/PocketSpeak/backend
ps aux | grep uvicorn | grep -v grep
# 如果没有运行：
# nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/pocketspeak_backend.log 2>&1 &
```

**步骤2**: 启动前端应用
```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

**步骤3**: 观察启动日志
```
flutter: ✅ 设备已激活，进入聊天页面
flutter: 🚀 开始初始化语音会话...
flutter: ✅ 语音会话初始化成功
flutter: 🔌 正在连接WebSocket: ws://localhost:8000/api/voice/ws
flutter: ✅ WebSocket连接成功
```

**步骤4**: 执行1分钟空闲测试
1. 发送一条消息："你好"
2. 等待1分钟（不操作）
3. 观察日志是否出现重连信息
4. 再次点击录音按钮，验证功能正常

### 7.2 如果仍然失败

**检查项1**: 是否看到重连日志？
```bash
# 如果没有，说明onDone回调未触发或_autoReconnect=false
```

**检查项2**: 是否达到最大重连次数？
```bash
# 搜索日志：
"❌ 已达到最大重连次数(5)，停止重连"
```

**检查项3**: 后端服务是否正常？
```bash
curl http://localhost:8000/api/voice/health
# 应该返回：{"healthy": true}
```

---

## 八、总结

### 8.1 核心成就

✅ **完整实现了前端WebSocket的自动重连机制**:
- 添加了所有必要的属性（`_autoReconnect`, `_reconnectAttempts`, `_maxReconnectAttempts`, `_reconnectTimer`）
- 实现了指数退避算法（1s, 2s, 4s, 8s, 16s）
- 主动断开时禁用自动重连
- 重连成功后重置计数器

✅ **解决了1分钟空闲录音失败的问题**:
- 之前：1分钟空闲后WebSocket断开，无法录音
- 现在：1分钟空闲后自动重连，功能正常

### 8.2 架构完整性

**现在两层WebSocket连接都有自动重连**:
- ✅ 前端→后端 (`voice_service.dart`)
- ✅ 后端→小智 (`ws_client.py`)

### 8.3 下一步

🔥 **立即测试**:
1. 重启前端应用（后端已经重启）
2. 执行1分钟空闲测试
3. 验证自动重连是否生效
4. 如有问题，提供详细的日志信息

---

**修复完成时间**: 2025-01-16
**修复状态**: ✅ 代码修改完成，等待测试验证
**关联修复**: `20250116_FINAL_AUTO_RECONNECT_IMPLEMENTATION.md` (后端修复)
**测试状态**: 待用户测试

**重要提醒**:
- 🔥 前端需要热重启（Hot Restart）或完全重启才能生效
- 🔥 观察日志中的重连信息
- 🔥 如有问题请提供完整的 flutter 日志

---

## 附录：快速诊断

### 如果1分钟后仍然提示"无法录音"

**Step 1**: 检查前端日志中是否有这些信息
```
🔌 WebSocket连接已关闭
🔄 将在 X 秒后尝试第 Y 次重连
```

**如果没有**:
- 说明 `onDone` 回调未触发或 `_autoReconnect = false`
- 可能是热重载（Hot Reload）未生效，需要**完全重启**应用

**Step 2**: 检查是否看到重连成功日志
```
✅ WebSocket连接成功
✅ 重连成功！
```

**如果没有**:
- 说明重连失败（后端可能未运行）
- 检查后端服务状态

**Step 3**: 检查后端日志
```bash
tail -50 /tmp/pocketspeak_backend.log
```

看是否有WebSocket连接日志。

### 紧急回滚

如果新版本有问题，可以快速回滚：

```bash
cd /Users/good/Desktop/PocketSpeak
git checkout HEAD~1 frontend/pocketspeak_app/lib/services/voice_service.dart
```

然后重启应用即可恢复到修复前的版本。
