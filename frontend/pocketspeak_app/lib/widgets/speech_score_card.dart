// 语音评分卡片组件 - PocketSpeak V1.6
// 紧凑内联文本样式，节省聊天区域空间

import 'package:flutter/material.dart';
import '../models/speech_feedback.dart';

class SpeechScoreCard extends StatelessWidget {
  final SpeechFeedbackResponse feedback;
  final VoidCallback? onGrammarTap;
  final VoidCallback? onPronunciationTap;
  final VoidCallback? onExpressionTap;

  const SpeechScoreCard({
    Key? key,
    required this.feedback,
    this.onGrammarTap,
    this.onPronunciationTap,
    this.onExpressionTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white,  // 添加白色背景
        border: Border.all(
          color: Colors.grey.shade300,
          width: 1,
        ),
        borderRadius: BorderRadius.circular(100),  // 使用大值实现半圆效果
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 4,
        children: [
          // 语法状态
          _buildGrammarChip(),
          // 发音评分
          _buildPronunciationChip(),
          // 表达地道程度
          _buildExpressionChip(),
        ],
      ),
    );
  }

  /// 构建语法状态标签
  Widget _buildGrammarChip() {
    final bool hasError = feedback.grammar.hasError;

    return GestureDetector(
      onTap: hasError ? onGrammarTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: hasError
              ? Colors.red.shade50
              : Colors.green.withOpacity(0.1),  // 语法正确也添加背景色
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              hasError ? Icons.error : Icons.check,
              size: 14,
              color: hasError ? Colors.red : Colors.green,
            ),
            const SizedBox(width: 3),
            Text(
              hasError ? '语法有误' : '语法正确',
              style: TextStyle(
                fontSize: 12,
                color: hasError ? Colors.red : Colors.green,
                fontWeight: FontWeight.w600,  // 加粗字体，与其他标签一致
              ),
            ),
            if (hasError) ...[
              const SizedBox(width: 3),
              Icon(
                Icons.chevron_right,
                size: 12,
                color: Colors.red.shade300,
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建发音评分标签
  Widget _buildPronunciationChip() {
    final int score = feedback.pronunciation.score;
    final Color color = _getPronunciationColor(score);

    return GestureDetector(
      onTap: onPronunciationTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '发音$score',
              style: TextStyle(
                fontSize: 12,
                color: color,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '发音分析>',
              style: TextStyle(
                fontSize: 10,
                color: color.withOpacity(0.7),
                height: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建表达地道程度标签
  Widget _buildExpressionChip() {
    final String level = feedback.expression.level;
    final Color color = _getExpressionColor(level);

    // 提取地道程度的数字表示 (非常地道=100, 地道=90, 一般=70, 不地道=50)
    final int levelScore = _getLevelScore(level);

    return GestureDetector(
      onTap: onExpressionTap,  // 始终可点击,查看表达优化详情
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '地道$levelScore',
              style: TextStyle(
                fontSize: 12,
                color: color,
                fontWeight: FontWeight.w600,
              ),
            ),
            // 始终显示"更多语境>"链接
            Text(
              '更多语境>',
              style: TextStyle(
                fontSize: 10,
                color: color.withOpacity(0.7),
                height: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============ 辅助方法 ============

  /// 获取发音得分颜色
  Color _getPronunciationColor(int score) {
    if (score >= 90) return Colors.green;
    if (score >= 80) return Colors.lightGreen.shade700;
    if (score >= 70) return Colors.orange;
    return Colors.deepOrange;
  }

  /// 获取表达地道程度颜色
  Color _getExpressionColor(String level) {
    switch (level) {
      case '非常地道':
        return Colors.green;
      case '地道':
        return Colors.lightGreen.shade700;
      case '一般':
        return Colors.orange;
      case '不地道':
        return Colors.deepOrange;
      default:
        return Colors.grey;
    }
  }

  /// 获取地道程度的数字评分
  int _getLevelScore(String level) {
    switch (level) {
      case '非常地道':
        return 100;
      case '地道':
        return 90;
      case '一般':
        return 70;
      case '不地道':
        return 50;
      default:
        return 60;
    }
  }
}
