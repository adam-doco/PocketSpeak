// 表达优化弹窗组件 - PocketSpeak V1.6
// 显示表达地道程度和优化建议

import 'package:flutter/material.dart';
import '../models/speech_feedback.dart';

class ExpressionImprovementModal extends StatelessWidget {
  final ExpressionEvaluation expression;
  final String originalText; // 原始文本（从GrammarAnalysis获取）

  const ExpressionImprovementModal({
    Key? key,
    required this.expression,
    required this.originalText,
  }) : super(key: key);

  /// 静态方法：显示表达优化弹窗
  static void show(
    BuildContext context,
    ExpressionEvaluation expression,
    String originalText,
  ) {
    showDialog(
      context: context,
      builder: (context) => ExpressionImprovementModal(
        expression: expression,
        originalText: originalText,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 400),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            _buildTitle(),
            const SizedBox(height: 20),
            // 地道程度标签
            _buildLevelBadge(),
            const SizedBox(height: 20),
            // 当前表达
            _buildCurrentExpression(),
            const SizedBox(height: 16),
            // 分隔线（带箭头）
            if (expression.suggestion != null) ...[
              _buildDivider(),
              const SizedBox(height: 16),
              // 建议表达
              _buildSuggestion(),
              const SizedBox(height: 16),
            ],
            // AI解释
            if (expression.reason != null) _buildReason(),
            const SizedBox(height: 24),
            // 关闭按钮
            _buildCloseButton(context),
          ],
        ),
      ),
    );
  }

  /// 构建标题
  Widget _buildTitle() {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.orange.shade50,
            shape: BoxShape.circle,
          ),
          child: Icon(
            Icons.chat_bubble_outline,
            color: Colors.orange.shade600,
            size: 24,
          ),
        ),
        const SizedBox(width: 12),
        const Text(
          '表达优化',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  /// 构建地道程度标签
  Widget _buildLevelBadge() {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: _getLevelColor(expression.level).withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: _getLevelColor(expression.level),
            width: 2,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getLevelIcon(expression.level),
              color: _getLevelColor(expression.level),
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              expression.level,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: _getLevelColor(expression.level),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建当前表达
  Widget _buildCurrentExpression() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.text_fields, size: 16, color: Colors.grey.shade600),
            const SizedBox(width: 6),
            Text(
              '当前表达',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey.shade300, width: 1),
          ),
          child: Text(
            originalText,
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey.shade800,
              height: 1.5,
            ),
          ),
        ),
      ],
    );
  }

  /// 构建分隔线（带箭头）
  Widget _buildDivider() {
    return Row(
      children: [
        Expanded(
          child: Divider(
            color: Colors.grey.shade300,
            thickness: 1,
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Icon(
            Icons.arrow_downward,
            color: Colors.grey.shade400,
            size: 20,
          ),
        ),
        Expanded(
          child: Divider(
            color: Colors.grey.shade300,
            thickness: 1,
          ),
        ),
      ],
    );
  }

  /// 构建建议表达
  Widget _buildSuggestion() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.stars, size: 16, color: Colors.green.shade600),
            const SizedBox(width: 6),
            Text(
              '优化建议',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.green.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.green.shade200, width: 1),
          ),
          child: Text(
            expression.suggestion ?? '无优化建议',
            style: TextStyle(
              fontSize: 16,
              color: Colors.green.shade700,
              height: 1.5,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  /// 构建AI解释
  Widget _buildReason() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade200, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb_outline, size: 16, color: Colors.blue.shade600),
              const SizedBox(width: 6),
              Text(
                'AI 解释',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.blue.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            expression.reason ?? '无详细解释',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade700,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建关闭按钮
  Widget _buildCloseButton(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: () => Navigator.pop(context),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.deepPurple,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        child: const Text(
          '知道了',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: Colors.white,
          ),
        ),
      ),
    );
  }

  // ============ 辅助方法 ============

  /// 获取地道程度颜色
  Color _getLevelColor(String level) {
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

  /// 获取地道程度图标
  IconData _getLevelIcon(String level) {
    switch (level) {
      case '非常地道':
        return Icons.star;
      case '地道':
        return Icons.check_circle;
      case '一般':
        return Icons.info;
      case '不地道':
        return Icons.warning;
      default:
        return Icons.help;
    }
  }
}
