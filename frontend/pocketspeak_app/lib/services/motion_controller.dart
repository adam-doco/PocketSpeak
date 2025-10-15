import 'package:flutter/foundation.dart';
import '../widgets/live2d_widget.dart';
import '../models/emotion_mapping.dart';
import 'emotion_mapper.dart';
import 'emoji_detector.dart';

/// 动作播放控制器
///
/// 负责根据emoji控制Live2D模型的动作和表情播放
class MotionController {
  final Live2DController? live2dController;
  final EmotionMapper _mapper;

  MotionController(this.live2dController)
      : _mapper = EmotionMapper.withDefaultMappings();

  /// 根据文本中的emoji播放对应的动作和表情
  ///
  /// 会自动从文本中提取第一个emoji并播放对应的动作
  /// 返回true表示成功触发播放，false表示未找到emoji或播放失败
  Future<bool> playEmotionFromText(String text) async {
    // 提取emoji
    final emoji = EmojiDetector.extractFirstEmoji(text);
    if (emoji == null) {
      debugPrint('⚠️ 文本中未找到emoji: $text');
      return false;
    }

    // 播放对应的情绪
    return await playEmotionByEmoji(emoji);
  }

  /// 根据emoji播放对应的动作和表情
  ///
  /// 返回true表示成功播放，false表示控制器未初始化或未找到映射
  Future<bool> playEmotionByEmoji(String emoji) async {
    if (live2dController == null) {
      debugPrint('⚠️ Live2D控制器未初始化，无法播放情绪');
      return false;
    }

    // 查找映射
    final mapping = _mapper.findMapping(emoji);
    if (mapping == null) {
      debugPrint('⚠️ 未找到emoji映射: $emoji，使用默认待机动作');
      // 播放默认待机动作
      await live2dController!.playMotion('', 0);
      return false;
    }

    debugPrint('🎭 播放情绪: ${mapping.emotionName} (emoji: $emoji)');
    await _playMapping(mapping);
    return true;
  }

  /// 执行映射的动作和表情播放
  Future<void> _playMapping(EmotionMapping mapping) async {
    if (live2dController == null) return;

    try {
      // 先播放动作
      if (mapping.motionIndex != null) {
        await live2dController!.playMotion(
          mapping.motionGroup ?? '',
          mapping.motionIndex!,
        );
        debugPrint('  ✓ 动作播放完成: ${mapping.motionGroup}:${mapping.motionIndex}');
      }

      // 等待一小段时间，避免动作和表情冲突
      if (mapping.motionIndex != null && mapping.expression != null) {
        await Future.delayed(const Duration(milliseconds: 100));
      }

      // 再播放表情
      if (mapping.expression != null) {
        await live2dController!.playExpression(mapping.expression!);
        debugPrint('  ✓ 表情播放完成: ${mapping.expression}');
      }

      debugPrint('🎭 情绪播放完成: ${mapping.emotionName}');
    } catch (e) {
      debugPrint('❌ 播放情绪失败: ${mapping.emotionName}, 错误: $e');
    }
  }

  /// 播放默认待机动作
  Future<void> playIdleMotion() async {
    if (live2dController == null) {
      debugPrint('⚠️ Live2D控制器未初始化');
      return;
    }

    debugPrint('🎭 播放待机动作');
    await live2dController!.playMotion('', 0);
  }

  /// 获取映射统计信息
  Map<String, dynamic> getStatistics() {
    return _mapper.getStatistics();
  }

  /// 检查是否支持指定的emoji
  bool supportsEmoji(String emoji) {
    return _mapper.hasMapping(emoji);
  }

  /// 获取所有支持的emoji列表
  List<String> getSupportedEmojis() {
    return _mapper.getSupportedEmojis();
  }
}
