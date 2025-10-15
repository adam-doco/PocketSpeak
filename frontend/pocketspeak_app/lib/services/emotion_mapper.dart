import 'package:flutter/foundation.dart';
import '../models/emotion_mapping.dart';

/// 情绪映射管理器
///
/// 负责根据emoji查找对应的动作和表情配置
class EmotionMapper {
  final List<EmotionMapping> _mappings;

  EmotionMapper(this._mappings);

  /// 使用默认映射配置创建实例
  factory EmotionMapper.withDefaultMappings() {
    return EmotionMapper(emotionMappings);
  }

  /// 根据emoji查找对应的情绪映射
  ///
  /// 如果找到映射则返回对应的EmotionMapping，否则返回null
  EmotionMapping? findMapping(String emoji) {
    try {
      final mapping = _mappings.firstWhere(
        (m) => m.emoji == emoji,
      );
      debugPrint('🎭 找到emoji映射: $emoji -> ${mapping.emotionName}');
      return mapping;
    } catch (e) {
      debugPrint('⚠️ 未找到emoji映射: $emoji');
      return null;
    }
  }

  /// 检查emoji是否有对应的映射
  bool hasMapping(String emoji) {
    return _mappings.any((m) => m.emoji == emoji);
  }

  /// 获取所有支持的emoji列表
  List<String> getSupportedEmojis() {
    return _mappings.map((m) => m.emoji).toList();
  }

  /// 获取映射统计信息
  Map<String, dynamic> getStatistics() {
    int withMotion = 0;
    int withExpression = 0;
    int withBoth = 0;

    for (final mapping in _mappings) {
      final hasMotion = mapping.motionIndex != null;
      final hasExpression = mapping.expression != null;

      if (hasMotion && hasExpression) {
        withBoth++;
      } else if (hasMotion) {
        withMotion++;
      } else if (hasExpression) {
        withExpression++;
      }
    }

    return {
      'total': _mappings.length,
      'with_motion_only': withMotion,
      'with_expression_only': withExpression,
      'with_both': withBoth,
    };
  }
}
