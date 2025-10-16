/// Live2D 表情映射数据模型
///
/// 用于将AI返回的emoji映射到Live2D模型的动作(Motion)和表情(Expression)

class EmotionMapping {
  /// AI返回的emoji字符
  final String emoji;

  /// 动作组名（空字符串表示默认组）
  final String? motionGroup;

  /// 动作索引
  final int? motionIndex;

  /// 表情名称
  final String? expression;

  /// 情绪名称（用于日志和调试）
  final String emotionName;

  const EmotionMapping({
    required this.emoji,
    this.motionGroup,
    this.motionIndex,
    this.expression,
    required this.emotionName,
  });

  @override
  String toString() {
    return 'EmotionMapping{emoji: $emoji, emotionName: $emotionName, '
        'motion: ${motionGroup ?? ""}:$motionIndex, expression: $expression}';
  }
}

/// 所有emoji到动作/表情的映射配置
///
/// 可用动作 (Motion):
/// - 0: Idle (待机)
/// - 1: jingya (惊讶)
/// - 2: kaixin (开心)
/// - 3: shengqi (生气)
/// - 4: wink (眨眼)
/// - 5: yaotou (摇头)
///
/// 可用表情 (Expression):
/// - A1爱心眼
/// - A2生气
/// - A3星星眼
/// - A4哭哭
/// - B1麦克风
/// - B2外套
/// - 舌头
const List<EmotionMapping> emotionMappings = [
  // 1. 😶 - neutral (中性)
  EmotionMapping(
    emoji: '😶',
    motionGroup: '',
    motionIndex: 0, // Idle
    emotionName: '中性',
  ),

  // 2. 😊 - smile (微笑)
  EmotionMapping(
    emoji: '😊',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: 'A1爱心眼',
    emotionName: '微笑',
  ),

  // 3. 🙂 - happy (开心)
  EmotionMapping(
    emoji: '🙂',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: 'A1爱心眼',
    emotionName: '开心',
  ),

  // 4. 😆 - laughing (大笑)
  EmotionMapping(
    emoji: '😆',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: 'A1爱心眼',
    emotionName: '大笑',
  ),

  // 5. 😂 - funny (搞笑)
  EmotionMapping(
    emoji: '😂',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: 'A1爱心眼',
    emotionName: '搞笑',
  ),

  // 6. 😔 - sad (难过)
  EmotionMapping(
    emoji: '😔',
    motionGroup: '',
    motionIndex: 0, // Idle
    expression: 'A4哭哭',
    emotionName: '难过',
  ),

  // 7. 😠 - angry (生气)
  EmotionMapping(
    emoji: '😠',
    motionGroup: '',
    motionIndex: 3, // shengqi
    expression: 'A2生气',
    emotionName: '生气',
  ),

  // 8. 😭 - crying (大哭)
  EmotionMapping(
    emoji: '😭',
    motionGroup: '',
    motionIndex: 0, // Idle
    expression: 'A4哭哭',
    emotionName: '大哭',
  ),

  // 9. 😍 - loving (爱慕)
  EmotionMapping(
    emoji: '😍',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: 'A1爱心眼',
    emotionName: '爱慕',
  ),

  // 10. 😳 - embarrassed (尴尬)
  EmotionMapping(
    emoji: '😳',
    motionGroup: '',
    motionIndex: 1, // jingya
    emotionName: '尴尬',
  ),

  // 11. 😲 - surprised (惊讶)
  EmotionMapping(
    emoji: '😲',
    motionGroup: '',
    motionIndex: 1, // jingya
    expression: 'A3星星眼',
    emotionName: '惊讶',
  ),

  // 12. 😱 - shocked (震惊)
  EmotionMapping(
    emoji: '😱',
    motionGroup: '',
    motionIndex: 1, // jingya
    expression: 'A3星星眼',
    emotionName: '震惊',
  ),

  // 13. 🤔 - thinking (思考)
  EmotionMapping(
    emoji: '🤔',
    motionGroup: '',
    motionIndex: 0, // Idle
    emotionName: '思考',
  ),

  // 14. 😉 - winking (眨眼)
  EmotionMapping(
    emoji: '😉',
    motionGroup: '',
    motionIndex: 4, // wink
    emotionName: '眨眼',
  ),

  // 15. 😎 - cool (酷)
  EmotionMapping(
    emoji: '😎',
    motionGroup: '',
    motionIndex: 2, // kaixin
    emotionName: '酷',
  ),

  // 16. 😌 - relaxed (放松)
  EmotionMapping(
    emoji: '😌',
    motionGroup: '',
    motionIndex: 0, // Idle
    emotionName: '放松',
  ),

  // 17. 🤤 - delicious (美味)
  EmotionMapping(
    emoji: '🤤',
    motionGroup: '',
    motionIndex: 2, // kaixin
    expression: '舌头',
    emotionName: '美味',
  ),

  // 18. 😘 - kissy (亲亲)
  EmotionMapping(
    emoji: '😘',
    motionGroup: '',
    motionIndex: 4, // wink
    expression: 'A1爱心眼',
    emotionName: '亲亲',
  ),

  // 19. 😏 - confident (自信)
  EmotionMapping(
    emoji: '😏',
    motionGroup: '',
    motionIndex: 2, // kaixin
    emotionName: '自信',
  ),

  // 20. 😴 - sleepy (困倦)
  EmotionMapping(
    emoji: '😴',
    motionGroup: '',
    motionIndex: 0, // Idle
    emotionName: '困倦',
  ),

  // 21. 😜 - silly (调皮)
  EmotionMapping(
    emoji: '😜',
    motionGroup: '',
    motionIndex: 4, // wink
    expression: '舌头',
    emotionName: '调皮',
  ),

  // 22. 🙄 - confused (困惑)
  EmotionMapping(
    emoji: '🙄',
    motionGroup: '',
    motionIndex: 5, // yaotou
    emotionName: '困惑',
  ),
];

/// 获取emoji对应的映射配置
EmotionMapping? getEmotionMapping(String emoji) {
  try {
    return emotionMappings.firstWhere(
      (mapping) => mapping.emoji == emoji,
    );
  } catch (e) {
    // 未找到映射，返回null
    return null;
  }
}
