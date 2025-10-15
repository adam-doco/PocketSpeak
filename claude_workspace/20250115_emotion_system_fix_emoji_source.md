# Live2D表情系统修复：处理独立emoji字段

**任务日期**: 2025-01-15
**任务类型**: Bug修复
**问题**: 表情系统无法识别emoji，因为emoji不在文本中，而是作为独立字段返回

---

## 一、问题分析

### 1.1 原始设计的错误假设

最初的设计假设emoji会包含在AI返回的文本中，所以使用`EmojiDetector.extractFirstEmoji(text)`从文本中提取emoji。

**原始代码**:
```dart
_voiceService.onTextReceived = (String text) {
  // ...显示消息...

  // 🎭 根据emoji播放对应的表情和动作
  if (_motionController != null) {
    _motionController!.playEmotionFromText(text);  // ❌ 错误：文本中没有emoji
  }
};
```

**实际情况**:
```
flutter: 📝 [WebSocket] 收到AI文本: 哎呀，被你拆穿了啦～
flutter: ⚠️ 文本中未找到emoji: 哎呀，被你拆穿了啦～
```

### 1.2 实际的数据结构

根据用户说明，大语言模型会使用1个token来输出emoji来表示当前的心情，这个emoji**不会被TTS朗读出来**，但是会被以**独立数据类型**进行返回。

**后端返回的消息格式**:
```json
{
  "type": "llm",
  "text": "😊",
  "emotion": "smile"
}
```

其中：
- `type`: 消息类型为"llm"
- `text`: emoji字符本身（如"😊"）
- `emotion`: 英文描述（如"smile"），可选

---

## 二、解决方案

### 2.1 修改 `voice_service.dart`

#### 2.1.1 添加emotion回调

**文件**: `lib/services/voice_service.dart`

**修改位置**: 第22-27行

```dart
// 🚀 音频帧回调（模仿py-xiaozhi的即时播放）
void Function(String audioData)? onAudioFrameReceived;
void Function(String text)? onUserTextReceived;  // 用户语音识别文字
void Function(String text)? onTextReceived;  // AI文本
void Function(String emoji)? onEmotionReceived;  // ✅ 新增：AI表情emoji
void Function(String state)? onStateChanged;
```

#### 2.1.2 处理"llm"类型的WebSocket消息

**修改位置**: 第486-500行

```dart
case 'llm':
  // 🎭 收到LLM消息（包含emoji表情）
  // 示例: {"type":"llm", "text": "😊", "emotion": "smile"}
  if (data['text'] != null) {
    // 如果text就是emoji，触发emotion回调
    if (onEmotionReceived != null) {
      onEmotionReceived!(data['text']);
    }
  }
  // 如果有独立的emotion字段也可以使用
  if (data['emotion'] != null && onEmotionReceived != null) {
    // emotion字段可能是英文描述，但我们主要使用text中的emoji
    print('🎭 收到emotion: ${data['emotion']}');
  }
  break;
```

#### 2.1.3 清理回调时包含新增的emotion回调

**修改位置**: 第535-540行

```dart
// 清空回调，防止重复触发
onAudioFrameReceived = null;
onUserTextReceived = null;
onTextReceived = null;
onEmotionReceived = null;  // ✅ 新增
onStateChanged = null;
```

### 2.2 修改 `chat_page.dart`

#### 2.2.1 移除从文本中提取emoji的逻辑

**文件**: `lib/pages/chat_page.dart`

**修改位置**: 第130-151行

**修改前**:
```dart
_voiceService.onTextReceived = (String text) {
  // ...显示消息...

  // 🎭 根据emoji播放对应的表情和动作
  if (_motionController != null) {
    _motionController!.playEmotionFromText(text);  // ❌ 错误
  }
};
```

**修改后**:
```dart
_voiceService.onTextReceived = (String text) {
  // ✅ 保留关键文本日志（低频）
  _debugLog('📝 [WebSocket] 收到AI文本: $text');

  // 🚀 只在流式模式下显示（避免与轮询重复）
  if (_useStreamingPlayback) {
    setState(() {
      final aiMessage = ChatMessage(
        messageId: 'ai_${DateTime.now().millisecondsSinceEpoch}',
        text: text,
        isUser: false,
        timestamp: DateTime.now(),
        hasAudio: false,
      );
      _messages.add(aiMessage);
      _isProcessing = false;
    });
    _typingController.stop();
    _scrollToBottom();
  }
};
```

#### 2.2.2 添加独立的emotion回调处理

**新增位置**: 第153-161行

```dart
// 🎭 收到AI表情emoji
_voiceService.onEmotionReceived = (String emoji) {
  _debugLog('🎭 [WebSocket] 收到emotion: $emoji');

  // 播放对应的表情和动作
  if (_motionController != null) {
    _motionController!.playEmotionByEmoji(emoji);
  }
};
```

---

## 三、工作流程对比

### 3.1 修复前的流程（错误）

```
AI返回文本消息 → onTextReceived回调
      ↓
尝试从文本中提取emoji
      ↓
❌ 文本中没有emoji，无法播放表情
```

### 3.2 修复后的流程（正确）

```
后端发送两条消息:
1. {"type":"text", "data":"哎呀，被你拆穿了啦～"}
      ↓
   onTextReceived回调 → 显示AI文本消息

2. {"type":"llm", "text":"😊", "emotion":"smile"}
      ↓
   onEmotionReceived回调 → 播放emoji对应的表情
      ↓
   MotionController.playEmotionByEmoji("😊")
      ↓
   查找映射表 → 播放动作+表情
```

---

## 四、修改的文件清单

### 4.1 修改的文件

1. **`lib/services/voice_service.dart`**
   - 第22-27行：添加`onEmotionReceived`回调
   - 第486-500行：添加"llm"消息类型的处理
   - 第535-540行：在disconnect时清理emotion回调

2. **`lib/pages/chat_page.dart`**
   - 第130-151行：移除从文本中提取emoji的错误逻辑
   - 第153-161行：添加独立的emotion回调处理

---

## 五、测试验证

### 5.1 预期行为

当AI回复时，应该看到以下日志：

```
flutter: 📝 [WebSocket] 收到AI文本: 哎呀，被你拆穿了啦～
flutter: 🎭 [WebSocket] 收到emotion: 😊
flutter: 🎭 找到emoji映射: 😊 -> 开心
flutter:   ✓ 动作播放完成: :2
flutter:   ✓ 表情播放完成: A1爱心眼
flutter: 🎭 情绪播放完成: 开心
```

### 5.2 测试步骤

1. 重新运行应用
2. 发送语音或文本消息给AI
3. 观察AI回复时：
   - 文本是否正常显示
   - 是否收到emotion日志
   - Live2D模型是否播放了对应的表情和动作

---

## 六、关键要点

1. **emoji不在文本中**: emoji作为独立的WebSocket消息发送，类型为"llm"
2. **单独处理**: onTextReceived用于显示文本，onEmotionReceived用于播放表情
3. **消息类型**: 需要在WebSocket消息处理中添加对"llm"类型的支持
4. **回调清理**: 断开连接时要记得清理新增的onEmotionReceived回调

---

## 七、后续优化建议

1. **错误处理**: 如果收到不在映射表中的emoji，可以记录日志并播放默认待机动作
2. **性能优化**: 可以缓存emoji到表情的映射，避免重复查找
3. **扩展性**: 如果后续需要支持更多emoji，只需要在`emotion_mapping.dart`中添加配置即可

---

**修复完成时间**: 2025-01-15
**修复状态**: ✅ 完成，等待测试验证
