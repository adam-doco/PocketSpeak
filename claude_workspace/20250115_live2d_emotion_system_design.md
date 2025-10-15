# Live2D 表情系统设计文档

**文档版本**: V1.0
**创建日期**: 2025-01-15
**任务目标**: 设计并实现 PocketSpeak 的 Live2D 表情自动映射与播放系统

---

## 一、需求概述

### 1.1 核心需求
小智AI在回复用户时会返回emoji表情，系统需要自动识别这些emoji并映射到Live2D模型的对应动作和表情，实现情感表达的可视化。

### 1.2 关键特性
1. **Emoji识别**: 自动从AI回复文本中提取emoji
2. **情绪映射**: 将emoji映射到模型的动作(Motion)和表情(Expression)
3. **自动播放**: 识别到emoji后自动触发对应的Live2D动画
4. **嘴部动画同步**: 语音播放时循环播放嘴部动作，语音结束时停止

---

## 二、系统架构

### 2.1 模块组成

```
┌─────────────────────────────────────────────────┐
│           Live2D Emotion System                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐      ┌─────────────────┐ │
│  │  Emoji Detector  │─────→│ Emotion Mapper  │ │
│  │  (识别emoji)      │      │  (映射情绪)      │ │
│  └──────────────────┘      └─────────────────┘ │
│           │                        │            │
│           ↓                        ↓            │
│  ┌──────────────────┐      ┌─────────────────┐ │
│  │  Motion Player   │      │  Lip Sync       │ │
│  │  (播放动作表情)   │      │  (嘴部同步)      │ │
│  └──────────────────┘      └─────────────────┘ │
│           │                        │            │
│           └────────────┬───────────┘            │
│                        ↓                        │
│              ┌──────────────────┐               │
│              │  Live2D Model    │               │
│              │  (模型渲染)       │               │
│              └──────────────────┘               │
└─────────────────────────────────────────────────┘
```

### 2.2 工作流程

```
AI返回文本 → 识别Emoji → 查找映射表 → 播放动作/表情
                                    ↓
                            (如果有语音) → 循环播放嘴部动作
                                    ↓
                            语音结束 → 停止嘴部动作 → 恢复待机状态
```

---

## 三、技术方案

### 3.1 Emoji映射表设计

#### 3.1.1 数据结构

```dart
class EmotionMapping {
  final String emoji;          // AI返回的emoji
  final String? motionGroup;   // 动作组名（空字符串表示默认组）
  final int? motionIndex;      // 动作索引
  final String? expression;    // 表情名称
  final String emotionName;    // 情绪名称（用于日志和调试）

  EmotionMapping({
    required this.emoji,
    this.motionGroup,
    this.motionIndex,
    this.expression,
    required this.emotionName,
  });
}
```

#### 3.1.2 映射表示例

根据现有的Live2D资源（来自 `live2d_test_page.dart`）：

**可用动作 (Motion)**:
- 0: Idle (待机)
- 1: jingya (惊讶)
- 2: kaixin (开心)
- 3: shengqi (生气)
- 4: wink (眨眼)
- 5: yaotou (摇头)

**可用表情 (Expression)**:
- A1爱心眼
- A2生气
- A3星星眼
- A4哭哭
- B1麦克风
- B2外套
- 舌头

**映射表配置**:

```dart
final List<EmotionMapping> emotionMappings = [
  // 开心类
  EmotionMapping(
    emoji: '😊',
    motionGroup: '',
    motionIndex: 2,  // kaixin
    expression: 'A1爱心眼',
    emotionName: '开心',
  ),
  EmotionMapping(
    emoji: '😄',
    motionGroup: '',
    motionIndex: 2,
    expression: 'A1爱心眼',
    emotionName: '开心',
  ),
  EmotionMapping(
    emoji: '🥰',
    motionGroup: '',
    motionIndex: 2,
    expression: 'A1爱心眼',
    emotionName: '喜欢',
  ),

  // 惊讶类
  EmotionMapping(
    emoji: '😮',
    motionGroup: '',
    motionIndex: 1,  // jingya
    expression: 'A3星星眼',
    emotionName: '惊讶',
  ),
  EmotionMapping(
    emoji: '😲',
    motionGroup: '',
    motionIndex: 1,
    expression: 'A3星星眼',
    emotionName: '震惊',
  ),

  // 生气类
  EmotionMapping(
    emoji: '😠',
    motionGroup: '',
    motionIndex: 3,  // shengqi
    expression: 'A2生气',
    emotionName: '生气',
  ),
  EmotionMapping(
    emoji: '😡',
    motionGroup: '',
    motionIndex: 3,
    expression: 'A2生气',
    emotionName: '愤怒',
  ),

  // 伤心类
  EmotionMapping(
    emoji: '😢',
    motionGroup: '',
    motionIndex: 0,  // Idle
    expression: 'A4哭哭',
    emotionName: '伤心',
  ),
  EmotionMapping(
    emoji: '😭',
    motionGroup: '',
    motionIndex: 0,
    expression: 'A4哭哭',
    emotionName: '大哭',
  ),

  // 俏皮类
  EmotionMapping(
    emoji: '😉',
    motionGroup: '',
    motionIndex: 4,  // wink
    emotionName: '眨眼',
  ),
  EmotionMapping(
    emoji: '😜',
    motionGroup: '',
    motionIndex: 4,
    expression: '舌头',
    emotionName: '调皮',
  ),

  // 否定类
  EmotionMapping(
    emoji: '🙅',
    motionGroup: '',
    motionIndex: 5,  // yaotou
    emotionName: '摇头',
  ),
  EmotionMapping(
    emoji: '❌',
    motionGroup: '',
    motionIndex: 5,
    emotionName: '否定',
  ),

  // 默认待机
  EmotionMapping(
    emoji: '🤔',
    motionGroup: '',
    motionIndex: 0,  // Idle
    emotionName: '思考',
  ),
];
```

### 3.2 Emoji识别器

```dart
class EmojiDetector {
  /// 从文本中提取第一个emoji
  static String? extractEmoji(String text) {
    final emojiRegex = RegExp(
      r'[\u{1F600}-\u{1F64F}]|'  // 表情符号
      r'[\u{1F300}-\u{1F5FF}]|'  // 符号和象形文字
      r'[\u{1F680}-\u{1F6FF}]|'  // 交通和地图符号
      r'[\u{1F700}-\u{1F77F}]|'  // 炼金术符号
      r'[\u{1F780}-\u{1F7FF}]|'  // 几何形状扩展
      r'[\u{1F800}-\u{1F8FF}]|'  // 补充箭头-C
      r'[\u{1F900}-\u{1F9FF}]|'  // 补充符号和象形文字
      r'[\u{1FA00}-\u{1FA6F}]|'  // 象棋符号
      r'[\u{1FA70}-\u{1FAFF}]|'  // 符号和象形文字扩展-A
      r'[\u{2600}-\u{26FF}]|'    // 杂项符号
      r'[\u{2700}-\u{27BF}]',    // 装饰符号
      unicode: true,
    );

    final match = emojiRegex.firstMatch(text);
    return match?.group(0);
  }

  /// 提取文本中所有emoji
  static List<String> extractAllEmojis(String text) {
    final emojiRegex = RegExp(
      r'[\u{1F600}-\u{1F64F}]|'
      r'[\u{1F300}-\u{1F5FF}]|'
      r'[\u{1F680}-\u{1F6FF}]|'
      r'[\u{1F700}-\u{1F77F}]|'
      r'[\u{1F780}-\u{1F7FF}]|'
      r'[\u{1F800}-\u{1F8FF}]|'
      r'[\u{1F900}-\u{1F9FF}]|'
      r'[\u{1FA00}-\u{1FA6F}]|'
      r'[\u{1FA70}-\u{1FAFF}]|'
      r'[\u{2600}-\u{26FF}]|'
      r'[\u{2700}-\u{27BF}]',
      unicode: true,
    );

    return emojiRegex.allMatches(text)
        .map((match) => match.group(0)!)
        .toList();
  }
}
```

### 3.3 情绪映射管理器

```dart
class EmotionMapper {
  final List<EmotionMapping> _mappings;

  EmotionMapper(this._mappings);

  /// 根据emoji查找对应的情绪映射
  EmotionMapping? findMapping(String emoji) {
    return _mappings.firstWhere(
      (mapping) => mapping.emoji == emoji,
      orElse: () => EmotionMapping(
        emoji: emoji,
        motionGroup: '',
        motionIndex: 0,  // 默认待机动作
        emotionName: '默认',
      ),
    );
  }
}
```

### 3.4 动作播放控制器

```dart
class MotionController {
  final Live2DController? live2dController;

  MotionController(this.live2dController);

  /// 根据emoji播放对应的动作和表情
  Future<void> playEmotionByEmoji(String emoji) async {
    if (live2dController == null) {
      debugPrint('⚠️ Live2D控制器未初始化');
      return;
    }

    final mapper = EmotionMapper(emotionMappings);
    final mapping = mapper.findMapping(emoji);

    if (mapping == null) {
      debugPrint('⚠️ 未找到emoji映射: $emoji');
      return;
    }

    debugPrint('🎭 播放情绪: ${mapping.emotionName} (emoji: $emoji)');

    // 先播放动作
    if (mapping.motionIndex != null) {
      await live2dController!.playMotion(
        mapping.motionGroup ?? '',
        mapping.motionIndex!,
      );
    }

    // 再播放表情
    if (mapping.expression != null) {
      await live2dController!.playExpression(mapping.expression!);
    }
  }
}
```

### 3.5 嘴部同步控制器

```dart
class LipSyncController {
  final Live2DController? live2dController;
  bool _isPlaying = false;
  Timer? _lipSyncTimer;

  LipSyncController(this.live2dController);

  /// 开始嘴部动画（语音播放时调用）
  void startLipSync() {
    if (_isPlaying || live2dController == null) return;

    _isPlaying = true;
    debugPrint('👄 开始嘴部同步动画');

    // 循环播放嘴部动作（假设使用B1麦克风表情）
    _lipSyncTimer = Timer.periodic(
      const Duration(milliseconds: 200),
      (timer) async {
        if (!_isPlaying) {
          timer.cancel();
          return;
        }
        await live2dController!.playExpression('B1麦克风');
      },
    );
  }

  /// 停止嘴部动画（语音结束时调用）
  void stopLipSync() {
    if (!_isPlaying) return;

    _isPlaying = false;
    _lipSyncTimer?.cancel();
    _lipSyncTimer = null;

    debugPrint('👄 停止嘴部同步动画');

    // 恢复待机状态
    live2dController?.playMotion('', 0);
  }

  void dispose() {
    stopLipSync();
  }
}
```

---

## 四、集成方案

### 4.1 在ChatPage中集成

```dart
class _ChatPageState extends State<ChatPage> {
  // Live2D控制器
  Live2DController? _live2dController;

  // 情绪控制器
  late MotionController _motionController;
  late LipSyncController _lipSyncController;

  @override
  void initState() {
    super.initState();
    _motionController = MotionController(null);
    _lipSyncController = LipSyncController(null);
  }

  void _onLive2DControllerCreated(Live2DController controller) {
    setState(() {
      _live2dController = controller;
      _motionController = MotionController(controller);
      _lipSyncController = LipSyncController(controller);
    });
    print('🎭 Live2D控制器已创建');
  }

  // 当收到AI回复时调用
  void _onAIMessageReceived(String message) {
    // 1. 识别emoji
    final emoji = EmojiDetector.extractEmoji(message);

    if (emoji != null) {
      // 2. 播放对应的表情和动作
      _motionController.playEmotionByEmoji(emoji);
    }
  }

  // 当开始播放语音时调用
  void _onAudioPlayStart() {
    _lipSyncController.startLipSync();
  }

  // 当语音播放结束时调用
  void _onAudioPlayEnd() {
    _lipSyncController.stopLipSync();
  }

  @override
  void dispose() {
    _lipSyncController.dispose();
    super.dispose();
  }
}
```

### 4.2 集成点识别

需要在以下位置插入表情触发逻辑：

1. **AI消息接收处** (`chat_page.dart`):
   - 在 `_handleWebSocketMessage()` 中，当收到 `ai_response` 类型消息时
   - 提取emoji并触发表情播放

2. **语音播放开始处** (`streaming_audio_player.dart`):
   - 在 `play()` 方法开始播放时
   - 触发 `LipSyncController.startLipSync()`

3. **语音播放结束处** (`streaming_audio_player.dart`):
   - 在 `_playNextInQueue()` 完成播放时
   - 在队列清空时
   - 触发 `LipSyncController.stopLipSync()`

---

## 五、待完善的emoji映射表

以下是需要补充的emoji映射（需要根据小智AI实际返回的emoji进行扩展）：

| Emoji分类 | Emoji示例 | 映射到的动作 | 映射到的表情 | 备注 |
|---------|----------|------------|------------|------|
| 开心 | 😊😄😃🥰😍 | kaixin(2) | A1爱心眼 | |
| 惊讶 | 😮😲🤯😱 | jingya(1) | A3星星眼 | |
| 生气 | 😠😡🤬 | shengqi(3) | A2生气 | |
| 伤心 | 😢😭😞😔 | Idle(0) | A4哭哭 | |
| 俏皮 | 😉😜😝 | wink(4) | 舌头 | |
| 否定 | 🙅❌🙅‍♀️ | yaotou(5) | - | |
| 思考 | 🤔💭 | Idle(0) | - | |
| 唱歌/说话 | 🎤🎵🎶 | - | B1麦克风 | 用于语音播放时 |

**需要用户提供的信息**：
- 小智AI会返回哪些emoji？
- 是否有特殊的emoji组合规则？
- 是否需要根据上下文调整映射策略？

---

## 六、实施步骤

### 6.1 Phase 1: 基础架构搭建
- [ ] 创建 `emotion_mapping.dart` 文件，定义数据结构
- [ ] 创建 `emoji_detector.dart` 文件，实现emoji识别
- [ ] 创建 `emotion_mapper.dart` 文件，实现映射查找
- [ ] 创建 `motion_controller.dart` 文件，实现动作播放控制
- [ ] 创建 `lip_sync_controller.dart` 文件，实现嘴部同步

### 6.2 Phase 2: 映射表配置
- [ ] 收集小智AI会返回的所有emoji
- [ ] 完善emoji到动作/表情的映射表
- [ ] 测试每个emoji的播放效果
- [ ] 调整映射表以达到最佳效果

### 6.3 Phase 3: 集成到ChatPage
- [ ] 在 `_handleWebSocketMessage()` 中集成emoji识别
- [ ] 在AI消息接收时触发表情播放
- [ ] 在语音播放时触发嘴部同步
- [ ] 测试整体流程

### 6.4 Phase 4: 优化与测试
- [ ] 测试表情切换的流畅度
- [ ] 测试嘴部同步的准确性
- [ ] 处理边界情况（如连续多个emoji、无emoji等）
- [ ] 性能优化

---

## 七、技术注意事项

### 7.1 动作/表情播放冲突
- **问题**: 动作(Motion)和表情(Expression)可能会互相覆盖
- **解决方案**:
  - 先播放动作，等待一小段时间后播放表情
  - 使用 `await` 确保动作播放完成后再播放表情

### 7.2 嘴部动画频率
- **问题**: 嘴部动画刷新频率需要与语音同步
- **解决方案**:
  - 使用 `Timer.periodic` 以固定频率刷新
  - 初始频率设为200ms，后续根据效果调整

### 7.3 emoji识别准确性
- **问题**: 不同平台emoji编码可能不同
- **解决方案**:
  - 使用Unicode范围匹配
  - 测试iOS和Android平台的兼容性

### 7.4 性能考虑
- **问题**: 频繁调用WebView可能影响性能
- **解决方案**:
  - 缓存当前播放状态，避免重复播放
  - 使用防抖(debounce)避免过于频繁的调用

---

## 八、测试计划

### 8.1 单元测试
- [ ] 测试emoji识别准确性
- [ ] 测试映射查找功能
- [ ] 测试边界情况处理

### 8.2 集成测试
- [ ] 测试AI消息触发表情播放
- [ ] 测试语音播放触发嘴部动画
- [ ] 测试动作和表情组合播放

### 8.3 用户体验测试
- [ ] 测试表情切换是否自然
- [ ] 测试嘴部同步是否流畅
- [ ] 测试整体情感表达效果

---

## 九、后续优化方向

1. **智能情绪分析**: 除了emoji，还可以通过NLP分析文本情感
2. **表情队列**: 支持播放一系列连续表情
3. **随机待机动作**: 待机时随机播放小动作，增加生动性
4. **语音分析**: 根据语音的音量、音调调整嘴部动画幅度
5. **情绪记忆**: 记住上一次的情绪状态，实现更自然的过渡

---

## 十、参考资料

- Live2D模型资源: `/Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app/assets/live2d/models/Mould/`
- Live2D测试页面: `/Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app/lib/pages/live2d_test_page.dart`
- Live2D Widget: `/Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app/lib/widgets/live2d_widget.dart`
- 聊天页面: `/Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app/lib/pages/chat_page.dart`

---

**文档状态**: ✅ 设计完成，等待用户确认后开始实施
