# PocketSpeak 流式音频播放架构设计方案

**日期**: 2025-01-07
**任务**: 改造PocketSpeak为Zoev4式流式播放架构，消除句子间延迟
**执行人**: Claude
**状态**: 🔧 设计阶段

---

## 🎯 目标

**彻底移除句子概念，实现音频帧级别的流式播放，延迟降至<150ms**

---

## 📊 架构对比

### 当前架构（PocketSpeak V1.0）

```
┌─────────────────────────────────────────────────────────────────┐
│                          后端流程                                │
└─────────────────────────────────────────────────────────────────┘
WebSocket接收 → 解析JSON → 判断type
                              ├─ AUDIO: 累积到_pcm_chunks
                              ├─ TEXT: 标记句子边界 ← 问题1
                              └─ TTS: 标记句子完成  ← 问题2

┌─────────────────────────────────────────────────────────────────┐
│                          前端流程                                │
└─────────────────────────────────────────────────────────────────┘
每30ms轮询 ← 问题3
  ↓
检查is_complete=True ← 问题4
  ↓
加入_sentenceQueue
  ↓
等待上一句播放完成 ← 问题5
  ↓
播放当前句子

延迟累积: 200ms(TEXT等待) + 15ms(轮询) + 35ms(播放回调) = 250ms
```

### 目标架构（Zoev4式流式播放）

```
┌─────────────────────────────────────────────────────────────────┐
│                          后端流程                                │
└─────────────────────────────────────────────────────────────────┘
WebSocket接收 → 解析JSON → 判断type
                              ├─ AUDIO: 立即推送给前端 ✅
                              ├─ TEXT: 仅用于显示文字 ✅
                              └─ TTS: 仅用于停止轮询 ✅

┌─────────────────────────────────────────────────────────────────┐
│                          前端流程                                │
└─────────────────────────────────────────────────────────────────┘
WebSocket监听音频推送 ✅
  ↓
收到音频帧立即处理
  ↓
第一帧: 立即播放
后续帧: 追加到播放队列
  ↓
无需等待句子完整

延迟: 0ms(无TEXT等待) + 0ms(无轮询) + 10ms(WebSocket推送) = 10ms
```

---

## 🏗️ 详细实施方案

### 阶段1: 后端改造（核心）

#### 1.1 修改 `voice_session_manager.py`

**目标**: 音频帧到达立即推送，不等TEXT消息

**修改位置**: `_on_ws_message_received` 方法

**原逻辑**:
```python
async def _on_ws_message_received(self, message: str):
    parsed_response = self.ws_client.parse_message(message)

    if parsed_response.message_type == MessageType.AUDIO:
        # 仅累积，不推送
        self.current_message.append_audio_chunk(audio_data)

    elif parsed_response.message_type == MessageType.TEXT:
        # 等TEXT到达才标记句子完成
        self.current_message.add_text_sentence(text)
```

**新逻辑**:
```python
async def _on_ws_message_received(self, message: str):
    parsed_response = self.ws_client.parse_message(message)

    if parsed_response.message_type == MessageType.AUDIO:
        # ✅ 音频帧到达，立即推送给所有前端
        audio_chunk = {
            "type": "audio_frame",
            "data": base64.b64encode(parsed_response.audio_data).decode('utf-8'),
            "format": "pcm",
            "sample_rate": 24000,
            "channels": 1,
            "timestamp": time.time()
        }

        # 广播给所有WebSocket连接
        await self._broadcast_audio_frame(audio_chunk)

        # 仍然累积到_pcm_chunks（用于历史记录）
        self.current_message.append_audio_chunk(audio_data)

    elif parsed_response.message_type == MessageType.TEXT:
        # ✅ TEXT仅用于显示文字气泡，不阻塞音频
        text_message = {
            "type": "text_sentence",
            "text": parsed_response.text_content,
            "timestamp": time.time()
        }

        # 推送文本消息（与音频独立）
        await self._broadcast_text_message(text_message)

        # 仍然保存句子（用于历史记录）
        self.current_message.add_text_sentence(parsed_response.text_content)
```

**新增方法**:
```python
async def _broadcast_audio_frame(self, audio_chunk: Dict[str, Any]):
    """广播音频帧到所有WebSocket客户端"""
    if not hasattr(self, '_ws_clients'):
        self._ws_clients = []

    for client in self._ws_clients:
        try:
            await client.send_json(audio_chunk)
        except Exception as e:
            logger.error(f"广播音频帧失败: {e}")

async def _broadcast_text_message(self, text_message: Dict[str, Any]):
    """广播文本消息到所有WebSocket客户端"""
    if not hasattr(self, '_ws_clients'):
        self._ws_clients = []

    for client in self._ws_clients:
        try:
            await client.send_json(text_message)
        except Exception as e:
            logger.error(f"广播文本消息失败: {e}")
```

---

#### 1.2 新增 WebSocket 推送端点

**文件**: `backend/routers/voice_chat.py`

**新增API**:
```python
@router.websocket("/ws/audio-stream")
async def websocket_audio_stream(websocket: WebSocket):
    """
    WebSocket端点用于实时音频流推送

    功能：
    1. 建立WebSocket连接
    2. 将客户端注册到session的广播列表
    3. 推送音频帧和文本消息
    """
    await websocket.accept()
    logger.info("🔗 WebSocket音频流客户端已连接")

    try:
        session = get_voice_session()
        if not session or not session.is_initialized:
            await websocket.send_json({
                "type": "error",
                "message": "语音会话未初始化"
            })
            await websocket.close()
            return

        # 注册客户端
        if not hasattr(session, '_ws_clients'):
            session._ws_clients = []
        session._ws_clients.append(websocket)

        # 发送欢迎消息
        await websocket.send_json({
            "type": "stream_ready",
            "message": "音频流已准备就绪",
            "session_id": session.session_id
        })

        # 保持连接
        while True:
            try:
                # 接收客户端消息（如果有控制指令）
                message = await websocket.receive_text()
                data = json.loads(message)

                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info("WebSocket客户端断开连接")
                break

    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)

    finally:
        # 移除客户端
        if hasattr(session, '_ws_clients') and websocket in session._ws_clients:
            session._ws_clients.remove(websocket)
        logger.info("WebSocket连接已清理")
```

---

### 阶段2: 前端改造（核心）

#### 2.1 创建 `StreamingAudioPlayer` 类

**文件**: `frontend/pocketspeak_app/lib/services/streaming_audio_player.dart`

**完整实现**:
```dart
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:just_audio/just_audio.dart';

/// 流式音频播放器（Zoev4式架构）
class StreamingAudioPlayer {
  // WebSocket连接
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  // 音频播放器
  final AudioPlayer _player = AudioPlayer();

  // 音频帧队列
  final List<Uint8List> _audioQueue = [];
  bool _isPlaying = false;

  // PCM累积缓冲区
  final List<int> _pcmBuffer = [];
  Timer? _flushTimer;

  // 回调
  Function(String text)? onTextReceived;
  Function()? onStreamComplete;

  /// 连接到后端WebSocket
  Future<bool> connect(String serverUrl) async {
    try {
      final wsUrl = serverUrl.replaceAll('http', 'ws') + '/ws/audio-stream';
      print('🔗 连接到音频流: $wsUrl');

      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      // 监听消息
      _subscription = _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
      );

      return true;
    } catch (e) {
      print('❌ WebSocket连接失败: $e');
      return false;
    }
  }

  /// 处理WebSocket消息
  void _onMessage(dynamic message) {
    if (message is String) {
      final data = jsonDecode(message);
      final type = data['type'] as String;

      if (type == 'audio_frame') {
        _handleAudioFrame(data);
      } else if (type == 'text_sentence') {
        _handleTextSentence(data);
      } else if (type == 'stream_ready') {
        print('✅ 音频流已准备就绪');
      }
    }
  }

  /// 处理音频帧
  void _handleAudioFrame(Map<String, dynamic> data) {
    // 解码Base64 PCM数据
    final audioData = base64Decode(data['data'] as String);

    // 添加到PCM缓冲区
    _pcmBuffer.addAll(audioData);

    // 启动定时flush（每50ms flush一次，避免过于频繁）
    _flushTimer?.cancel();
    _flushTimer = Timer(const Duration(milliseconds: 50), _flushPcmBuffer);
  }

  /// Flush PCM缓冲区到播放器
  void _flushPcmBuffer() {
    if (_pcmBuffer.isEmpty) return;

    // 将PCM转为WAV格式
    final wavData = _pcmToWav(Uint8List.fromList(_pcmBuffer));
    _audioQueue.add(wavData);
    _pcmBuffer.clear();

    print('🎵 音频帧入队: ${wavData.length} bytes, 队列长度=${_audioQueue.length}');

    // 如果没在播放，立即开始播放
    if (!_isPlaying) {
      _playNextChunk();
    }
  }

  /// 播放下一个音频块
  Future<void> _playNextChunk() async {
    if (_audioQueue.isEmpty) {
      _isPlaying = false;
      print('✅ 播放队列已清空');
      return;
    }

    _isPlaying = true;
    final chunk = _audioQueue.removeAt(0);

    try {
      // 使用just_audio播放WAV数据
      await _player.setAudioSource(
        _WavAudioSource(chunk),
        initialPosition: Duration.zero,
      );

      await _player.play();

      // 等待播放完成
      await _player.processingStateStream
          .firstWhere((state) => state == ProcessingState.completed);

      // 继续播放下一块
      _playNextChunk();

    } catch (e) {
      print('❌ 播放失败: $e');
      _isPlaying = false;
    }
  }

  /// 处理文本句子
  void _handleTextSentence(Map<String, dynamic> data) {
    final text = data['text'] as String;
    print('📝 收到文本: $text');

    if (onTextReceived != null) {
      onTextReceived!(text);
    }
  }

  /// PCM转WAV
  Uint8List _pcmToWav(Uint8List pcmData) {
    // WAV header (44 bytes)
    final sampleRate = 24000;
    final channels = 1;
    final bitsPerSample = 16;

    final dataSize = pcmData.length;
    final fileSize = 36 + dataSize;

    final buffer = ByteData(44 + dataSize);

    // RIFF header
    buffer.setUint8(0, 0x52); // 'R'
    buffer.setUint8(1, 0x49); // 'I'
    buffer.setUint8(2, 0x46); // 'F'
    buffer.setUint8(3, 0x46); // 'F'
    buffer.setUint32(4, fileSize, Endian.little);

    // WAVE header
    buffer.setUint8(8, 0x57);  // 'W'
    buffer.setUint8(9, 0x41);  // 'A'
    buffer.setUint8(10, 0x56); // 'V'
    buffer.setUint8(11, 0x45); // 'E'

    // fmt subchunk
    buffer.setUint8(12, 0x66); // 'f'
    buffer.setUint8(13, 0x6D); // 'm'
    buffer.setUint8(14, 0x74); // 't'
    buffer.setUint8(15, 0x20); // ' '
    buffer.setUint32(16, 16, Endian.little); // Subchunk1Size
    buffer.setUint16(20, 1, Endian.little);  // AudioFormat (PCM)
    buffer.setUint16(22, channels, Endian.little);
    buffer.setUint32(24, sampleRate, Endian.little);
    buffer.setUint32(28, sampleRate * channels * bitsPerSample ~/ 8, Endian.little); // ByteRate
    buffer.setUint16(32, channels * bitsPerSample ~/ 8, Endian.little); // BlockAlign
    buffer.setUint16(34, bitsPerSample, Endian.little);

    // data subchunk
    buffer.setUint8(36, 0x64); // 'd'
    buffer.setUint8(37, 0x61); // 'a'
    buffer.setUint8(38, 0x74); // 't'
    buffer.setUint8(39, 0x61); // 'a'
    buffer.setUint32(40, dataSize, Endian.little);

    // Copy PCM data
    for (var i = 0; i < dataSize; i++) {
      buffer.setUint8(44 + i, pcmData[i]);
    }

    return buffer.buffer.asUint8List();
  }

  void _onError(error) {
    print('❌ WebSocket错误: $error');
  }

  void _onDone() {
    print('🔌 WebSocket连接已关闭');
    if (onStreamComplete != null) {
      onStreamComplete!();
    }
  }

  /// 断开连接
  Future<void> disconnect() async {
    await _subscription?.cancel();
    await _channel?.sink.close();
    await _player.stop();
    await _player.dispose();
    _flushTimer?.cancel();
    print('🛑 流式播放器已关闭');
  }
}

/// 自定义AudioSource用于播放内存中的WAV数据
class _WavAudioSource extends StreamAudioSource {
  final Uint8List _wavData;

  _WavAudioSource(this._wavData);

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end ??= _wavData.length;

    return StreamAudioResponse(
      sourceLength: _wavData.length,
      contentLength: end - start,
      offset: start,
      stream: Stream.value(_wavData.sublist(start, end)),
      contentType: 'audio/wav',
    );
  }
}
```

---

#### 2.2 修改 `chat_page.dart`

**目标**: 移除句子轮询，改用流式播放器

**修改位置**: `_startSentencePlayback` 方法

**原逻辑**:
```dart
void _startSentencePlayback() {
  _sentencePollingTimer = Timer.periodic(
    const Duration(milliseconds: 30),
    (timer) async {
      final result = await _voiceService.getCompletedSentences(...);
      // 轮询获取句子...
    }
  );
}
```

**新逻辑**:
```dart
// 替换为流式播放器
StreamingAudioPlayer? _streamingPlayer;

Future<void> _startStreamingPlayback() async {
  // 创建流式播放器
  _streamingPlayer = StreamingAudioPlayer();

  // 设置回调
  _streamingPlayer!.onTextReceived = (text) {
    // 收到文本，创建气泡
    setState(() {
      final aiMessage = ChatMessage(
        messageId: 'ai_${DateTime.now().millisecondsSinceEpoch}',
        text: text,
        isUser: false,
        timestamp: DateTime.now(),
        hasAudio: false,  // 音频与文本解耦
      );
      _messages.add(aiMessage);
    });
    _scrollToBottom();
  };

  _streamingPlayer!.onStreamComplete = () {
    print('✅ AI回复完成');
    setState(() {
      _isProcessing = false;
    });
  };

  // 连接WebSocket
  final serverUrl = 'http://localhost:8000';
  final connected = await _streamingPlayer!.connect(serverUrl);

  if (connected) {
    print('✅ 流式播放已启动');
  } else {
    print('❌ 流式播放启动失败');
  }
}

void _stopStreamingPlayback() {
  _streamingPlayer?.disconnect();
  _streamingPlayer = null;
  print('🛑 流式播放已停止');
}
```

---

### 阶段3: 兼容性处理

#### 3.1 保留历史记录功能

**问题**: 移除句子后，如何存储历史对话？

**解决方案**:
- 后端仍然保留`_sentences`和`_pcm_chunks`累积逻辑
- 流式推送与历史记录并行运行
- 对话结束后，仍然可以从`get_conversation_history`获取完整记录

```python
# voice_session_manager.py
async def _on_ws_message_received(self, message: str):
    parsed_response = self.ws_client.parse_message(message)

    if parsed_response.message_type == MessageType.AUDIO:
        # ✅ 1. 立即推送（实时播放）
        await self._broadcast_audio_frame(audio_chunk)

        # ✅ 2. 累积保存（历史记录）
        self.current_message.append_audio_chunk(audio_data)
```

---

#### 3.2 文本与音频同步问题

**问题**: TEXT消息可能晚于AUDIO到达，导致气泡显示延迟

**解决方案**: 接受这个trade-off
- 优先保证音频播放流畅（延迟<50ms）
- 文本气泡可以稍晚显示（延迟100-200ms可接受）
- 用户感知：听到声音最重要，看到文字可以稍晚

---

### 阶段4: 测试验证

#### 4.1 延迟测试

**测试场景**: AI回复3句话，每句2秒

**测试指标**:
1. 第一句开始播放延迟: 目标<150ms
2. 句子间衔接延迟: 目标<50ms
3. 音频连续性: 无明显卡顿

**测试方法**:
```python
# 在voice_session_manager.py添加时间戳日志
async def _on_ws_message_received(self, message: str):
    timestamp = time.time()

    if parsed_response.message_type == MessageType.AUDIO:
        logger.info(f"⏰ 音频帧到达: {timestamp}")
        await self._broadcast_audio_frame(audio_chunk)
        logger.info(f"⏰ 音频帧推送完成: {time.time()}, 耗时={(time.time() - timestamp)*1000}ms")
```

```dart
// 在streaming_audio_player.dart添加日志
void _handleAudioFrame(Map<String, dynamic> data) {
  final receiveTime = DateTime.now().millisecondsSinceEpoch;
  print('⏰ 前端收到音频帧: $receiveTime');

  // ...处理逻辑

  print('⏰ 音频帧处理完成: ${DateTime.now().millisecondsSinceEpoch}, 耗时=${DateTime.now().millisecondsSinceEpoch - receiveTime}ms');
}
```

---

#### 4.2 稳定性测试

**测试场景**:
1. 连续10轮对话
2. 长句子（>10句）回复
3. 快速连续提问
4. 网络抖动模拟

**预期结果**:
- 无内存泄漏
- 无音频重叠或丢失
- WebSocket连接稳定

---

## 📋 实施清单

### 后端修改

- [ ] `voice_session_manager.py`
  - [ ] 新增 `_broadcast_audio_frame` 方法
  - [ ] 新增 `_broadcast_text_message` 方法
  - [ ] 修改 `_on_ws_message_received` 添加实时推送逻辑
  - [ ] 新增 `_ws_clients` 客户端列表管理

- [ ] `routers/voice_chat.py`
  - [ ] 新增 `/ws/audio-stream` WebSocket端点
  - [ ] 实现客户端注册与广播机制

### 前端修改

- [ ] 新建 `lib/services/streaming_audio_player.dart`
  - [ ] 实现 `StreamingAudioPlayer` 类
  - [ ] 实现 WebSocket连接管理
  - [ ] 实现音频帧累积与播放逻辑
  - [ ] 实现 PCM转WAV工具方法

- [ ] 修改 `lib/pages/chat_page.dart`
  - [ ] 移除 `_sentencePollingTimer` 相关逻辑
  - [ ] 新增 `_streamingPlayer` 实例
  - [ ] 修改 `_startSentencePlayback` 为 `_startStreamingPlayback`
  - [ ] 修改 `_stopSentencePlayback` 为 `_stopStreamingPlayback`
  - [ ] 调整文本气泡创建逻辑（回调触发）

### 测试验证

- [ ] 延迟测试
  - [ ] 添加时间戳日志
  - [ ] 测量第一句播放延迟
  - [ ] 测量句子间衔接延迟

- [ ] 稳定性测试
  - [ ] 连续10轮对话测试
  - [ ] 长句子回复测试
  - [ ] 快速连续提问测试

- [ ] 功能回归测试
  - [ ] 历史记录完整性
  - [ ] 文本气泡显示正确性
  - [ ] 录音功能正常

---

## ⚠️ 风险评估

### 高风险项

1. **just_audio兼容性** - 流式WAV播放可能有缓冲问题
   - **缓解方案**: 可考虑使用`audioplayers`包替代

2. **WebSocket稳定性** - 长时间连接可能断开
   - **缓解方案**: 实现心跳机制和自动重连

### 中风险项

1. **音频帧大小** - 过小导致频繁播放，过大导致延迟
   - **缓解方案**: 50ms flush间隔，动态调整

2. **TEXT与AUDIO不同步** - 气泡显示可能晚于音频
   - **缓解方案**: 接受trade-off，优先保证音频流畅

### 低风险项

1. **历史记录格式** - 保持现有逻辑，无影响

---

## 📊 预期效果

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 第一句播放延迟 | 315ms | <150ms | **-165ms** |
| 句子间衔接延迟 | 250ms | <50ms | **-200ms** |
| 总体流畅度 | ⭐⭐ | ⭐⭐⭐⭐⭐ | **显著提升** |
| 用户体验 | 卡顿明显 | 接近实时 | **质的飞跃** |

---

## 🚀 实施顺序

1. **Phase 1**: 后端WebSocket推送机制（2-3小时）
2. **Phase 2**: 前端流式播放器（3-4小时）
3. **Phase 3**: 集成测试与调优（2-3小时）
4. **Phase 4**: 稳定性验证（1-2小时）

**总计**: 8-12小时开发时间

---

**创建时间**: 2025-01-07 下午
**预计开始**: 立即
**预计完成**: 2025-01-07 晚上或次日
**文档状态**: 设计完成，等待实施
