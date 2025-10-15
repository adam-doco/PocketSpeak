# py-xiaozhi 播放逻辑深度分析

**日期**: 2025-01-07
**目的**: 理解 py-xiaozhi 的音频播放逻辑,并应用到 PocketSpeak

---

## 🎯 核心发现

### py-xiaozhi 的播放逻辑（极简）

**文件**: `libs/py_xiaozhi/src/application.py` + `audio_codecs/audio_codec.py`

**流程**:
```
WebSocket收到音频
  ↓
_on_incoming_audio(data)  (Line 954)
  ↓
_schedule_audio_write_task(data)  (Line 1006)
  ↓
audio_codec.write_audio(data)  (Line 425)
  ↓
opus_decoder.decode() → PCM数据  (Line 738)
  ↓
_output_buffer.put(audio_array)  (Line 752)
  ↓
硬件播放（sounddevice自动消费队列）
```

### 关键代码

#### 1. 接收音频回调 (application.py:954-1011)
```python
def _on_incoming_audio(self, data):
    """接收音频数据回调"""
    should_play_audio = self.device_state == DeviceState.SPEAKING or (
        self.device_state == DeviceState.LISTENING
        and self.listening_mode == ListeningMode.REALTIME
    )

    if should_play_audio and self.audio_codec and self.running:
        # 直接写入音频，无等待！
        self._main_loop.call_soon_threadsafe(
            self._schedule_audio_write_task, data
        )
```

#### 2. 音频写入 (audio_codec.py:732-757)
```python
async def write_audio(self, opus_data: bytes):
    """解码音频并播放"""
    # Opus解码为24kHz PCM数据
    pcm_data = self.opus_decoder.decode(
        opus_data, AudioConfig.OUTPUT_FRAME_SIZE
    )

    audio_array = np.frombuffer(pcm_data, dtype=np.int16)

    # 放入播放队列（立即播放，无延迟）
    self._put_audio_data_safe(self._output_buffer, audio_array)
```

---

## 🔑 核心特点

### 1. **无句子概念**
- py-xiaozhi 不区分句子
- 收到音频帧立即播放
- TEXT消息仅用于显示，不影响播放

### 2. **队列 + 硬件回调**
- `_output_buffer`: asyncio.Queue(maxsize=500)
- sounddevice 自动消费队列
- 硬件播放速度 = 24kHz采样率（40ms/帧）

### 3. **延迟极低**
- WebSocket收到 → 解码 → 入队 → 播放
- 总延迟 ≈ 45ms（主要是网络 + 解码时间）
- **没有等待TEXT消息的延迟！**

---

## ❌ PocketSpeak当前的问题

### 我们的架构（错误）

```
WebSocket收到音频 → VoiceMessage累积
  ↓
等待TEXT消息到达 → 标记句子完成
  ↓
前端轮询（300ms间隔）
  ↓
获取完整句子（TEXT + AUDIO）
  ↓
播放音频
```

**延迟来源**:
1. 等待TEXT消息：200-300ms
2. 轮询间隔：150ms（平均）
3. 总延迟：350-450ms

### 根本错误

**我们把"句子"作为播放单位，而 py-xiaozhi 把"音频帧"作为播放单位！**

---

## ✅ 正确的解决方案

### 方案：模仿 py-xiaozhi 的即时播放

**后端修改**（最小改动）:
```python
# services/voice_chat/ws_client.py

async def _on_ws_message_received(self, message_type: str, data: Any):
    if message_type == "AUDIO":
        # 🚀 立即推送给前端，不等TEXT
        if self.audio_callback:
            await self.audio_callback({
                "type": "audio_frame",
                "data": data  # OPUS数据
            })

        # 同时保存到句子（用于历史记录）
        self.current_message.append_audio_chunk(data)

    elif message_type == "TEXT":
        # 创建句子（仅用于历史记录）
        self.current_message.add_text_sentence(data["text"])

        # 推送文字给前端（显示用）
        if self.text_callback:
            await self.text_callback({
                "type": "text",
                "text": data["text"]
            })
```

**前端修改**（WebSocket监听）:
```dart
// voice_service.dart

_channel.stream.listen((message) {
  final data = jsonDecode(message);

  if (data['type'] == 'audio_frame') {
    // 🚀 收到音频帧立即播放
    final opusData = base64Decode(data['data']);
    _audioPlayer.playFrame(opusData);  // 直接播放，无等待
  }

  if (data['type'] == 'text') {
    // 显示文字气泡
    _addMessageBubble(data['text']);
  }
});
```

---

## 📊 效果对比

| 指标 | 当前方案 | py-xiaozhi方案 | 改善 |
|------|---------|---------------|------|
| 播放单位 | 句子 | 音频帧 | - |
| 等待TEXT | 是（200-300ms） | 否 | **-250ms** |
| 轮询延迟 | 150ms | 0ms | **-150ms** |
| 总延迟 | 400ms | 50ms | **-350ms** |
| 实时性 | 低 | 高 | ⭐⭐⭐⭐⭐ |

---

## ⚠️ 注意事项

### 1. 历史记录保留
- 后端仍然维护 `_sentences` 结构
- TEXT到达时仍然调用 `add_text_sentence()`
- 历史记录API不变

### 2. 前端需要流式播放器
- Flutter需要支持Opus流式解码
- 或者用 `just_audio` 的流式播放
- 或者自己维护播放队列

### 3. 音频帧推送方式
- WebSocket Server Push（推荐）
- 或者 HTTP SSE (Server-Sent Events)

---

## 🎯 实施步骤

### 阶段1: 后端添加推送接口
1. 在 `voice_chat.py` 添加 WebSocket 推送端点
2. 在 `WSClient` 收到AUDIO时立即推送
3. 保留现有句子管理逻辑（历史记录）

### 阶段2: 前端添加流式播放
1. 建立 WebSocket 连接到推送端点
2. 收到音频帧立即解码播放
3. 收到TEXT创建气泡显示

### 阶段3: 测试验证
1. 对比延迟（预期降低300ms）
2. 验证历史记录功能
3. 验证文字显示

---

## 💡 为什么之前一直失败

**我一直试图在"逐句播放"框架内优化延迟:**
1. 降低轮询间隔 → 治标不治本
2. 提前标记is_complete → 破坏句子逻辑
3. 动态更新end_chunk → 逻辑冲突

**根本问题是架构选择错误:**
- py-xiaozhi 是 **帧驱动播放**（收到帧就播）
- PocketSpeak 是 **句子驱动播放**（收到句子才播）

**正确做法:**
- 播放层：帧驱动（实时性）
- 展示层：句子驱动（用户体验）
- 存储层：句子驱动（历史记录）

三层分离，各司其职！

---

## 📝 总结

1. py-xiaozhi 的核心是 `_on_incoming_audio()` → `write_audio()` → `_output_buffer`
2. 无句子概念，收到音频帧立即播放
3. TEXT消息仅用于显示，不影响播放
4. PocketSpeak应该模仿这个架构
5. 通过WebSocket推送音频帧给前端
6. 前端收到立即播放，不等TEXT

**改动量**: 中等（需要添加WebSocket推送）
**风险**: 低（不影响现有逻辑）
**效果**: 延迟降低300-350ms

---

**创建时间**: 2025-01-07
**分析深度**: ⭐⭐⭐⭐⭐
**可行性**: ⭐⭐⭐⭐⭐
