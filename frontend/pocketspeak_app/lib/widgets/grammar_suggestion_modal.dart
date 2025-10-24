// 语法建议弹窗组件 - PocketSpeak V1.6
// 显示语法错误和修改建议

import 'package:flutter/material.dart';
import '../models/speech_feedback.dart';

class GrammarSuggestionModal extends StatelessWidget {
  final GrammarAnalysis grammar;

  const GrammarSuggestionModal({
    Key? key,
    required this.grammar,
  }) : super(key: key);

  /// 静态方法：显示语法建议弹窗
  static void show(BuildContext context, GrammarAnalysis grammar) {
    showDialog(
      context: context,
      builder: (context) => GrammarSuggestionModal(grammar: grammar),
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
            // 原始句子
            _buildOriginalSentence(),
            const SizedBox(height: 16),
            // 分隔线（带箭头）
            _buildDivider(),
            const SizedBox(height: 16),
            // 建议句子
            _buildSuggestion(),
            const SizedBox(height: 16),
            // AI解释
            _buildReason(),
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
            color: Colors.red.shade50,
            shape: BoxShape.circle,
          ),
          child: Icon(
            Icons.error_outline,
            color: Colors.red.shade600,
            size: 24,
          ),
        ),
        const SizedBox(width: 12),
        const Text(
          '语法建议',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  /// 构建原始句子
  Widget _buildOriginalSentence() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.text_fields, size: 16, color: Colors.grey.shade600),
            const SizedBox(width: 6),
            Text(
              '原始句子',
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
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.red.shade200, width: 1),
          ),
          child: Text(
            grammar.original,
            style: TextStyle(
              fontSize: 16,
              color: Colors.red.shade700,
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

  /// 构建建议句子
  Widget _buildSuggestion() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.check_circle_outline, size: 16, color: Colors.green.shade600),
            const SizedBox(width: 6),
            Text(
              '修改建议',
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
            grammar.suggestion ?? '无修改建议',
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
            grammar.reason ?? '无详细解释',
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
}
