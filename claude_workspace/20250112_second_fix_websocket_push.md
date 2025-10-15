# 🔧 第二次修复：WebSocket音频推送问题

**时间**: 2025-01-12
**优先级**: P0
**状态**: 已修复 → 等待测试

---

## 🎯 问题分析

### 用户反馈

1. ✅ **文字不重复了** - 第一次修复成功
2. ❌ **声音仍然卡顿** - 音频推送仍有问题

### 日志分析

**后端日志**：
```
INFO:services.voice_chat.voice_session_manager:✅ 流式OPUS解码器已初始化
```
- `_on_audio_received` 被调用了
- 解码器初始化成功

**但是前端日志**：
```
flutter: 🎵 启动连续播放循环
flutter: ✅ 连续播放循环结束  // ← 立即结束！
```
- **前端完全没有收到音频帧**
- 播放循环启动后立即结束（队列为空）

### 根本原因

**问题在于 `on_audio_frame` 回调的执行方式**：

原代码（voice_chat.py:826-833）：
```python
def on_audio_frame(audio_data: bytes):
    """收到音频帧立即推送"""
    import base64
    asyncio.create_task(websocket.send_json({
        "type": "audio_frame",
        "data": base64.b64encode(audio_data).decode('utf-8')
    }))
```

**问题**：
- `asyncio.create_task` 创建的任务可能不会立即执行
- 或者在某些情况下任务会被取消
- 没有错误处理，如果发送失败也不知道

---

## 🔧 修复方案

### 修复1: 使用 `run_coroutine_threadsafe` 确保任务执行

**文件**: `backend/routers/voice_chat.py` (826-845行)

**修改**：
```python
def on_audio_frame(audio_data: bytes):
    """收到音频帧立即推送（模仿py-xiaozhi的即时播放）"""
    import base64
    try:
        # 🔥 关键修复：使用 run_coroutine_threadsafe 确保任务真正执行
        loop = asyncio.get_event_loop()

        async def _send():
            try:
                await websocket.send_json({
                    "type": "audio_frame",
                    "data": base64.b64encode(audio_data).decode('utf-8')
                })
                logger.debug(f"✅ 音频帧已推送: {len(audio_data)} bytes")
            except Exception as e:
                logger.error(f"❌ WebSocket发送音频帧失败: {e}")

        asyncio.run_coroutine_threadsafe(_send(), loop)
    except Exception as e:
        logger.error(f"❌ on_audio_frame 回调失败: {e}", exc_info=True)
```

**关键改进**：
1. 使用 `run_coroutine_threadsafe` 替代 `create_task`
2. 添加异常处理
3. 添加日志追踪

### 修复2: 优化 `_on_audio_received` 日志

**文件**: `backend/services/voice_chat/voice_session_manager.py` (947-981行)

**修改**：
```python
def _on_audio_received(self, audio_data: AudioData):
    """
    当收到音频消息时的回调（解析器触发）
    🚀 在这里立即解码并推送音频帧给前端（模仿py-xiaozhi）
    """
    if self.on_audio_frame_received:
        try:
            import opuslib
            if not hasattr(self, '_streaming_opus_decoder'):
                self._streaming_opus_decoder = opuslib.Decoder(24000, 1)
                logger.info("✅ 流式OPUS解码器已初始化")
                self._audio_frame_count = 0

            # 解码OPUS为PCM
            pcm_data = self._streaming_opus_decoder.decode(
                audio_data.data,
                frame_size=960,
                decode_fec=False
            )

            # 调用回调推送给前端
            self.on_audio_frame_received(pcm_data)

            # 每10帧输出一次日志
            self._audio_frame_count += 1
            if self._audio_frame_count % 10 == 0:
                logger.info(f"🎵 已推送 {self._audio_frame_count} 帧音频")
        except Exception as e:
            logger.error(f"❌ 音频帧推送回调失败: {e}", exc_info=True)
    else:
        logger.warning("⚠️ on_audio_frame_received 回调未设置，音频帧未推送")
```

**关键改进**：
1. 添加帧计数器
2. 每10帧输出一次日志（避免日志过多）
3. 清晰的异常处理

---

## 🧪 测试步骤

### 步骤1: 重启后端

```bash
cd /Users/good/Desktop/PocketSpeak/backend
# Ctrl+C 停止
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤2: 测试

1. 启动前端
2. 说一句话
3. 观察日志

### 步骤3: 检查关键日志

**后端应该显示**：
```
✅ 流式OPUS解码器已初始化
🎵 已推送 10 帧音频
🎵 已推送 20 帧音频
...
```

**如果推送失败**：
```
❌ WebSocket发送音频帧失败: xxx
❌ on_audio_frame 回调失败: xxx
```

**前端应该显示**：
```
flutter: 🎵 启动连续播放循环
// 应该持续播放，不会立即结束
flutter: ✅ 连续播放循环结束  // ← 在所有音频播放完后才结束
```

---

## 🎯 py-xiaozhi vs PocketSpeak 架构对比

### py-xiaozhi（硬件驱动模式）

```
sounddevice.OutputStream
  ↓
stream callback (每40ms自动触发)
  ↓
从 asyncio.Queue 获取音频帧
  ↓
写入硬件缓冲区
  ↓
硬件自动播放（无缝连续）
```

**特点**：
- 硬件驱动，自动连续
- 无需手动循环
- 延迟极低（~40ms）

### PocketSpeak（文件播放模式）

```
WebSocket 收到音频帧
  ↓
累积到队列
  ↓
播放循环：
  - 取3帧（~120ms）
  - 写WAV文件
  - 设置播放路径
  - await 播放完成
  - 继续下一批
  ↓
每批之间有间隙（文件IO + 播放器切换）
```

**特点**：
- 文件播放，需要手动循环
- 每批之间有切换延迟
- 总延迟较高（取决于批次大小和IO速度）

### 关键差异

| 特性 | py-xiaozhi | PocketSpeak |
|------|-----------|-------------|
| 播放方式 | 硬件流式 | 文件播放 |
| 是否需要循环 | 否（自动） | 是（手动） |
| 延迟 | 40ms | 120ms+ |
| 连续性 | 完美无缝 | 有间隙 |
| 平台 | 桌面 | 移动端 |

---

## 🚨 如果仍然卡顿的可能原因

### 1. 前端仍未收到音频

**检查**：
- 后端是否有 "❌ WebSocket发送音频帧失败" 错误
- 前端是否有音频帧接收日志

**排查**：
```bash
# 后端日志搜索
grep "WebSocket发送音频帧失败" backend.log
grep "已推送.*帧音频" backend.log

# 前端日志搜索
# 查看是否有 addAudioFrame 调用
```

### 2. 前端播放逻辑有问题

**可能原因**：
- 批次大小不合适（太大导致延迟，太小导致切换频繁）
- WAV文件写入太慢
- just_audio 播放器切换有延迟

**优化方向**：
- 减小批次大小（1帧 = 40ms）
- 使用内存缓冲而非文件
- 预加载下一批

### 3. 网络延迟

**检查**：
- WebSocket延迟
- 音频帧到达频率

---

## 📊 预期效果

### 成功标志

**后端日志**：
```
✅ 流式OPUS解码器已初始化
🎵 已推送 10 帧音频
🎵 已推送 20 帧音频
🎵 已推送 30 帧音频
...
🎵 已推送 130 帧音频  // 约130帧 = 5.2秒音频
```

**前端日志**：
```
flutter: 🎵 启动连续播放循环
// 持续播放约5秒...
flutter: ✅ 连续播放循环结束
```

**用户体验**：
- 音频播放流畅
- 间隙感知不明显（<100ms）
- 整体可接受

### 如果仍有卡顿

需要进一步优化前端播放逻辑：
1. 调整批次大小
2. 优化文件IO
3. 考虑使用流式播放插件

---

**修复时间**: 2025-01-12
**测试状态**: 等待用户测试
**预期**: 前端能收到音频帧，但可能仍有轻微卡顿（受限于文件播放模式）
