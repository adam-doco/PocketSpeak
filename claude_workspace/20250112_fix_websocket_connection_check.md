# 🔧 修复：WebSocket 连接检查缺失

**时间**: 2025-01-12
**问题**: WebSocket 发送消息失败导致状态变为 error
**错误代码**: `received 1005 (no status code [internal])`
**根本原因**: `send_start_listening()` 和 `send_stop_listening()` 缺少 WebSocket 连接检查

---

## 📋 问题分析

### 错误日志

```
ERROR:services.voice_chat.ws_client:发送开始监听消息失败: received 1005 (no status code [internal]); then sent 1005 (no status code [internal])
ERROR:services.voice_chat.voice_session_manager:WebSocket错误: 发送开始监听消息失败...
INFO:services.voice_chat.voice_session_manager:会话状态变更: ready -> error
```

**WebSocket 错误代码 1005**: 连接异常关闭（没有收到预期的状态码）

### 问题流程

1. ✅ WebSocket 连接建立成功
2. ✅ 收到服务器 hello 确认（session_id=7184d19f）
3. ✅ 状态变更为 AUTHENTICATED
4. ❌ **发送"开始监听"消息时连接已断开**
5. ❌ 代码没有检测到连接断开，直接尝试发送
6. ❌ 抛出异常，状态变为 error
7. ❌ 第二次录音尝试被拒绝（当前状态 error）

---

## 🔍 根本原因

### 代码对比

**`send_start_listening()` 原代码**（第292-310行）:
```python
if self.state != ConnectionState.AUTHENTICATED:
    logger.warning("WebSocket未认证，无法发送开始监听消息")
    return False

if not self.session_id:
    logger.error("Session ID为空，无法发送开始监听消息")
    return False

try:
    message_json = json.dumps(message, ensure_ascii=False)
    await self.websocket.send(message_json)  # ← 没有检查连接！
```

**问题**：
- ✅ 检查了认证状态
- ✅ 检查了 session_id
- ❌ **没有检查 websocket 是否存在或已关闭**

**`send_message()` 对比**（第254-260行）（有检查）:
```python
if self.state != ConnectionState.AUTHENTICATED:
    return False

if not self.websocket:  # ← 有检查！
    logger.error("WebSocket连接不存在")
    return False

try:
    await self.websocket.send(message_json)
```

**`send_audio()` 对比**（第382-388行）（也有检查）:
```python
if self.state != ConnectionState.AUTHENTICATED:
    return False

if not self.websocket:  # ← 有检查！
    logger.error("WebSocket连接不存在")
    return False

try:
    await self.websocket.send(audio_data)
```

---

## 🔧 修复内容

### 文件修改

**文件**: `backend/services/voice_chat/ws_client.py`

### 修改1: `send_start_listening()` 添加连接检查

**位置**: 第296-298行（新增）

**新增代码**:
```python
if not self.websocket or self.websocket.closed:
    logger.error("WebSocket连接不存在或已关闭，无法发送开始监听消息")
    return False
```

**完整修改后**:
```python
async def send_start_listening(self, mode: str = "auto") -> bool:
    if self.state != ConnectionState.AUTHENTICATED:
        logger.warning("WebSocket未认证，无法发送开始监听消息")
        return False

    # 🔥 新增：检查 WebSocket 连接
    if not self.websocket or self.websocket.closed:
        logger.error("WebSocket连接不存在或已关闭，无法发送开始监听消息")
        return False

    if not self.session_id:
        logger.error("Session ID为空，无法发送开始监听消息")
        return False

    try:
        message_json = json.dumps(message, ensure_ascii=False)
        await self.websocket.send(message_json)
        # ...
```

### 修改2: `send_stop_listening()` 添加连接检查

**位置**: 第343-345行（新增）

**新增代码**:
```python
if not self.websocket or self.websocket.closed:
    logger.error("WebSocket连接不存在或已关闭，无法发送停止监听消息")
    return False
```

**完整修改后**:
```python
async def send_stop_listening(self) -> bool:
    if self.state != ConnectionState.AUTHENTICATED:
        logger.warning("WebSocket未认证，无法发送停止监听消息")
        return False

    # 🔥 新增：检查 WebSocket 连接
    if not self.websocket or self.websocket.closed:
        logger.error("WebSocket连接不存在或已关闭，无法发送停止监听消息")
        return False

    if not self.session_id:
        logger.error("Session ID为空，无法发送停止监听消息")
        return False

    try:
        message_json = json.dumps(message, ensure_ascii=False)
        await self.websocket.send(message_json)
        # ...
```

---

## 🎯 修复效果

### 修复前

```
✅ WebSocket连接建立成功
✅ 收到服务器hello确认
     ↓
尝试发送"开始监听"消息
     ↓
❌ 连接已断开但未检测到
     ↓
❌ 抛出异常：received 1005
     ↓
❌ 状态变为 error
     ↓
❌ 第二次录音无法开始
```

### 修复后

```
✅ WebSocket连接建立成功
✅ 收到服务器hello确认
     ↓
尝试发送"开始监听"消息
     ↓
✅ 检测到连接已断开
     ↓
✅ 返回 False（优雅失败）
     ↓
✅ 前端收到失败响应
     ↓
✅ 可以尝试重新连接
```

---

## ⚠️ 注意事项

### 连接断开的根本原因

这个修复**只是防止崩溃**，但不能解决连接断开的根本原因：

**可能的原因**:
1. **服务器端问题**: 服务器在 hello 后主动关闭连接
2. **网络问题**: 网络不稳定导致连接断开
3. **认证问题**: token 或 device_id 有问题导致服务器拒绝连接
4. **心跳问题**: 心跳机制未正常工作

**需要进一步诊断**:
- 检查服务器端日志
- 确认网络连接稳定性
- 验证认证信息是否正确
- 检查心跳机制是否正常

### 状态管理改进建议

当 WebSocket 连接断开时，应该：
1. ✅ 自动尝试重连（已实现：`_schedule_reconnect()`）
2. ⚠️ **重置会话状态**（可能需要改进）
3. ⚠️ **通知前端重新初始化**（可能需要改进）

---

## 🧪 测试步骤

### 1. 重启后端

```bash
cd /Users/good/Desktop/PocketSpeak/backend
# Ctrl+C 停止现有进程
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 重启前端（热重启）

在 Flutter 终端按 `R` 键（大写R）

### 3. 测试录音

说一句话："在吗？"

---

## 📊 预期日志

### 成功情况（连接正常）

```
INFO:services.voice_chat.ws_client:✅ WebSocket连接建立成功
INFO:services.voice_chat.ws_client:✅ 收到服务器hello确认, session_id=xxx
INFO:services.voice_chat.voice_session_manager:会话状态变更: initializing -> ready
INFO:routers.voice_chat:🎤 开始录音...
INFO:services.voice_chat.voice_session_manager:🎤 开始监听用户语音...
INFO:services.voice_chat.ws_client:📤 发送开始监听消息: mode=auto
```

### 失败情况（连接断开，但优雅处理）

```
INFO:services.voice_chat.ws_client:✅ WebSocket连接建立成功
INFO:services.voice_chat.ws_client:✅ 收到服务器hello确认, session_id=xxx
INFO:services.voice_chat.voice_session_manager:会话状态变更: initializing -> ready
INFO:routers.voice_chat:🎤 开始录音...
INFO:services.voice_chat.voice_session_manager:🎤 开始监听用户语音...
ERROR:services.voice_chat.ws_client:WebSocket连接不存在或已关闭，无法发送开始监听消息  ← 🔥 新日志
INFO:services.voice_chat.voice_session_manager:🔄 WebSocket连接断开，尝试重连...
```

---

## 🔄 后续工作

如果连接仍然频繁断开，需要：

1. **检查服务器端日志**
   - 服务器是否拒绝连接？
   - 是否有错误信息？

2. **验证认证信息**
   - device_id 是否正确？
   - token 是否有效？

3. **网络诊断**
   - 是否有防火墙阻止？
   - 网络是否稳定？

4. **改进重连机制**
   - 重连后是否需要重新认证？
   - 重连是否需要清理旧状态？

---

## 📝 总结

### 修改范围

- ✅ **1个文件**: `ws_client.py`
- ✅ **2处修改**: `send_start_listening()`, `send_stop_listening()`
- ✅ **每处新增3行代码**

### 核心改进

1. **一致性**: 所有发送方法现在都有连接检查
2. **容错性**: 连接断开时优雅失败，不会崩溃
3. **可维护性**: 统一的错误处理逻辑

### 风险

- ✅ **低风险**: 只是添加了防御性检查
- ✅ **易回滚**: 如果有问题可以删除检查
- ✅ **向后兼容**: 不影响现有功能

---

**修复完成时间**: 2025-01-12
**等待测试**: 重启后端 + 重启前端

**遵循规范**:
- ✅ 已查阅 Debug 规范文档
- ✅ 已分析根本原因
- ✅ 已记录完整修改日志
- ✅ 修改限定在问题模块内
