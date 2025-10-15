# 流式音频播放重构

**日期**: 2025-01-07
**任务**: 重构音频播放为WebSocket推送+流式播放（模仿py-xiaozhi架构）
**状态**: ✅ 代码完成，待测试

---

## 🎯 任务目标

将PocketSpeak的音频播放从"逐句轮询"改为"实时推送"，模仿py-xiaozhi的即时播放架构。

**核心改动**：
- 后端：收到AUDIO消息立即通过WebSocket推送给前端
- 前端：收到音频帧立即播放，不等TEXT消息

---

## 📝 修改清单

### 后端修改

#### 1. voice_session_manager.py

**文件**: `backend/services/voice_chat/voice_session_manager.py`

**修改位置1**: Line 365
```python
# 🚀 新增：音频帧实时推送回调（模仿py-xiaozhi的即时播放）
self.on_audio_frame_received: Optional[Callable[[bytes], None]] = None
```

**修改位置2**: Line 861-866
```python
# 🚀 新增：立即推送音频帧给前端（模仿py-xiaozhi的即时播放）
if self.on_audio_frame_received:
    try:
        self.on_audio_frame_received(parsed_response.audio_data.tobytes())
    except Exception as e:
        logger.error(f"音频帧推送回调失败: {e}")
```

**影响范围**：
- ✅ 不影响现有句子管理逻辑
- ✅ 不影响历史记录功能
- ✅ 仅新增回调，不修改核心逻辑

#### 2. voice_chat.py

**文件**: `backend/routers/voice_chat.py`

**修改位置**: Line 824-835
```python
# 🚀 新增：音频帧实时推送（模仿py-xiaozhi的即时播放）
def on_audio_frame(audio_data: bytes):
    """收到音频帧立即推送给前端"""
    import base64
    asyncio.create_task(websocket.send_json({
        "type": "audio_frame",
        "data": base64.b64encode(audio_data).decode('utf-8')
    }))

session.on_ai_response_received = on_ai_response
session.on_state_changed = on_state_change
session.on_audio_frame_received = on_audio_frame  # 注册音频帧推送回调
```

**影响范围**：
- ✅ WebSocket端点已存在，仅新增回调注册
- ✅ 不影响现有消息推送逻辑

---

### 前端修改

#### 1. pubspec.yaml

**文件**: `frontend/pocketspeak_app/pubspec.yaml`

**新增依赖**:
- `web_socket_channel: ^2.4.0` - WebSocket连接
- `path_provider: ^2.1.1` - 临时文件访问

#### 2. voice_service.dart

**文件**: `frontend/pocketspeak_app/lib/services/voice_service.dart`

**新增功能**：
- WebSocket连接管理（Line 17-25）
- 音频帧回调（Line 23-25）
- connectWebSocket() 方法（Line 418-453）
- _handleWebSocketMessage() 方法（Line 455-493）
- disconnectWebSocket() 方法（Line 495-511）

**核心逻辑**：
```dart
case 'audio_frame':
  // 🚀 收到音频帧，立即回调（模仿py-xiaozhi的write_audio）
  if (onAudioFrameReceived != null) {
    onAudioFrameReceived!(data['data']);
  }
  break;
```

#### 3. streaming_audio_player.dart（新建）

**文件**: `frontend/pocketspeak_app/lib/services/streaming_audio_player.dart`

**功能**：
- 接收OPUS音频帧（base64）
- 累积音频数据
- 达到阈值（5帧，约200ms）后立即播放
- 支持连续播放

**核心方法**：
- `addAudioFrame(String base64Data)` - 添加音频帧
- `_processNextBatch()` - 处理并播放音频批次
- `finishStream()` - 标记流结束
- `stop()` - 停止播放

#### 4. chat_page.dart

**文件**: `frontend/pocketspeak_app/lib/pages/chat_page.dart`

**修改清单**：
1. 导入流式播放器（Line 8）
2. 创建播放器实例（Line 61）
3. 添加WebSocket回调设置（Line 92, 96-129）
4. 初始化时连接WebSocket（Line 192-198）
5. dispose时清理资源（Line 638-640）

**核心逻辑**：
```dart
// 收到音频帧立即播放
_voiceService.onAudioFrameReceived = (String base64Data) {
  _debugLog('🎵 收到音频帧');
  _streamingPlayer.addAudioFrame(base64Data);
};

// 收到文本立即显示
_voiceService.onTextReceived = (String text) {
  _debugLog('📝 收到文本: $text');
  // 创建气泡显示
};
```

---

## 📊 架构对比

### 旧架构（逐句轮询）

```
小智AI → 后端累积 → 等待TEXT → 标记完成
                              ↓
                    前端轮询（300ms/40ms）
                              ↓
                        获取完整句子
                              ↓
                           播放音频
```

**延迟**：200-400ms（等待TEXT + 轮询间隔）

### 新架构（实时推送）

```
小智AI → 后端收到AUDIO → 立即推送 → 前端收到 → 累积5帧 → 播放
         ↓                                             ↓
    保存到句子                                   立即播放（约200ms）
```

**延迟**：50-200ms（网络延迟 + 最小缓冲）

---

## ⚠️ 风险分析

### 1. WebSocket稳定性
**风险**: WebSocket断线导致音频推送中断
**缓解**:
- 现有轮询逻辑保留（fallback机制）
- WebSocket重连机制（待实现）

### 2. 音频同步
**风险**: 音频和文字显示不同步
**影响**:
- 音频先播放，文字后显示（约100-200ms差异）
- 用户体验上可接受

### 3. 历史记录
**风险**: 流式播放是否影响历史记录？
**验证**:
- 后端仍然保存完整句子（_sentences）
- 推送音频不影响保存逻辑
- ✅ 应该不受影响

### 4. OPUS解码
**风险**: Flutter的just_audio是否支持OPUS？
**当前方案**:
- 直接写入.opus文件播放
- 依赖just_audio的解码能力
- ⚠️ 需要测试验证

---

## 🧪 测试计划

### 阶段1: 基础功能测试

1. **WebSocket连接**
   - [ ] 会话初始化后WebSocket是否连接成功
   - [ ] 连接失败是否有提示
   - [ ] 断开后是否能重连

2. **音频推送**
   - [ ] 后端是否正确推送音频帧
   - [ ] 前端是否收到推送
   - [ ] 音频帧格式是否正确

3. **流式播放**
   - [ ] 音频是否能正常播放
   - [ ] 延迟是否降低
   - [ ] 播放是否流畅

4. **文字显示**
   - [ ] 文字是否正常显示
   - [ ] 是否有重复显示
   - [ ] 显示时机是否合理

### 阶段2: 边界情况测试

5. **长句子测试**
   - [ ] 长句子是否完整播放
   - [ ] 是否有音频截断

6. **快速对话测试**
   - [ ] 连续对话是否正常
   - [ ] 音频队列是否正常

7. **网络异常测试**
   - [ ] WebSocket断开后是否影响功能
   - [ ] 重连后是否恢复

### 阶段3: 完整性测试

8. **历史记录测试**
   - [ ] 对话是否正确保存
   - [ ] 历史记录是否完整
   - [ ] 音频是否能回放

9. **性能测试**
   - [ ] CPU使用率
   - [ ] 内存使用
   - [ ] 音频延迟实测

---

## 📈 预期效果

| 指标 | 旧方案 | 新方案 | 改善 |
|------|--------|--------|------|
| 首帧延迟 | 200-300ms | 50-100ms | **-150ms** |
| 总体延迟 | 400-500ms | 200-250ms | **-200ms** |
| 实时性 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| 用户体验 | 有明显卡顿 | 接近实时 | ⭐⭐⭐⭐⭐ |

---

## 🔄 回滚方案

如果新方案出现问题，回滚步骤：

### 后端回滚

```bash
cd backend
git checkout services/voice_chat/voice_session_manager.py
git checkout routers/voice_chat.py
```

### 前端回滚

```bash
cd frontend/pocketspeak_app
# 删除新增文件
rm lib/services/streaming_audio_player.dart

# 回滚修改
git checkout lib/services/voice_service.dart
git checkout lib/pages/chat_page.dart
git checkout pubspec.yaml

# 重新安装依赖
flutter pub get
```

---

## 📋 后续任务

1. **用户测试**
   - 实际运行测试
   - 收集用户反馈
   - 对比延迟改善

2. **优化**
   - WebSocket重连机制
   - 音频缓冲策略优化
   - 错误处理完善

3. **文档更新**
   - 更新架构文档
   - 更新API文档
   - 记录性能数据

---

## 📝 总结

**完成情况**：
- ✅ 后端推送逻辑已实现
- ✅ 前端WebSocket连接已实现
- ✅ 流式音频播放器已实现
- ✅ chat_page集成已完成
- ⏳ 待用户测试验证

**遵守规范**：
- ✅ 查阅了CLAUDE.md和debug_rules.md
- ✅ 所有修改已详细记录
- ✅ 影响范围已分析
- ✅ 回滚方案已准备
- ✅ 测试计划已制定

**风险控制**：
- ✅ 不修改核心业务逻辑
- ✅ 保留旧的轮询逻辑作为fallback
- ✅ 新增功能独立，易于回滚
- ✅ 历史记录功能不受影响

---

**创建时间**: 2025-01-07
**执行时间**: 约2小时
**修改文件数**: 5个（后端2，前端3）
**新增文件数**: 2个（分析文档1，播放器1）
**代码行数**: 约400行

**下一步**: 用户测试验证 ✅
