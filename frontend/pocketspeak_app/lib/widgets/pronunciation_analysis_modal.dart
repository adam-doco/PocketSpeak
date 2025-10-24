// 发音分析弹窗组件 - PocketSpeak V1.6
// 显示详细的发音分析结果

import 'package:flutter/material.dart';
import '../models/speech_feedback.dart';

class PronunciationAnalysisModal extends StatelessWidget {
  final PronunciationDetail pronunciation;

  const PronunciationAnalysisModal({
    Key? key,
    required this.pronunciation,
  }) : super(key: key);

  /// 静态方法：显示发音分析弹窗
  static void show(BuildContext context, PronunciationDetail pronunciation) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => PronunciationAnalysisModal(
        pronunciation: pronunciation,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: Column(
        children: [
          // 顶部把手
          _buildHandle(),
          // 标题
          _buildTitle(),
          // 内容区域（可滚动）
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 总分展示
                  _buildOverallScore(),
                  const SizedBox(height: 24),
                  // 逐词打分
                  _buildWordByWordScore(),
                  const SizedBox(height: 24),
                  // 细分评分
                  _buildDetailedScores(),
                  const SizedBox(height: 24),
                  // 语速信息
                  _buildSpeedInfo(),
                  const SizedBox(height: 24),
                  // 系统建议
                  _buildSuggestion(),
                ],
              ),
            ),
          ),
          // 底部关闭按钮
          _buildCloseButton(context),
        ],
      ),
    );
  }

  /// 构建顶部把手
  Widget _buildHandle() {
    return Container(
      margin: const EdgeInsets.only(top: 12),
      width: 40,
      height: 4,
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  /// 构建标题
  Widget _buildTitle() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: [
          Icon(Icons.record_voice_over, color: Colors.deepPurple.shade400),
          const SizedBox(width: 8),
          const Text(
            '发音分析',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建总分展示
  Widget _buildOverallScore() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _getScoreColor(pronunciation.score).withOpacity(0.1),
          shape: BoxShape.circle,
          border: Border.all(
            color: _getScoreColor(pronunciation.score),
            width: 3,
          ),
        ),
        child: Column(
          children: [
            Text(
              '${pronunciation.score}',
              style: TextStyle(
                fontSize: 48,
                fontWeight: FontWeight.bold,
                color: _getScoreColor(pronunciation.score),
              ),
            ),
            Text(
              '发音得分',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建逐词打分
  Widget _buildWordByWordScore() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '单词发音详情',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: Colors.grey.shade800,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: pronunciation.words.map((word) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: _getWordStatusColor(word.status).withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _getWordStatusColor(word.status),
                  width: 1.5,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _getWordStatusIcon(word.status),
                    color: _getWordStatusColor(word.status),
                    size: 16,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    word.word,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _getWordStatusColor(word.status),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 12),
        // 状态说明
        _buildStatusLegend(),
      ],
    );
  }

  /// 构建状态图例
  Widget _buildStatusLegend() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildLegendItem(Icons.check_circle, Colors.green, '正确'),
          const SizedBox(width: 16),
          _buildLegendItem(Icons.warning, Colors.orange, '待提高'),
          const SizedBox(width: 16),
          _buildLegendItem(Icons.cancel, Colors.red, '错误'),
        ],
      ),
    );
  }

  Widget _buildLegendItem(IconData icon, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 14),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  /// 构建细分评分
  Widget _buildDetailedScores() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '评分细节',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: Colors.grey.shade800,
          ),
        ),
        const SizedBox(height: 12),
        _buildScoreBar('流利度', pronunciation.fluency, Icons.trending_up),
        const SizedBox(height: 10),
        _buildScoreBar('清晰度', pronunciation.clarity, Icons.volume_up),
        const SizedBox(height: 10),
        _buildScoreBar('完整度', pronunciation.completeness, Icons.check_circle_outline),
      ],
    );
  }

  /// 构建评分条
  Widget _buildScoreBar(String label, int score, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: Colors.grey.shade600),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
              ),
            ),
            const Spacer(),
            Text(
              '$score',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: _getScoreColor(score),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: score / 100,
            backgroundColor: Colors.grey.shade200,
            valueColor: AlwaysStoppedAnimation<Color>(_getScoreColor(score)),
            minHeight: 8,
          ),
        ),
      ],
    );
  }

  /// 构建语速信息
  Widget _buildSpeedInfo() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200, width: 1),
      ),
      child: Row(
        children: [
          Icon(Icons.speed, color: Colors.blue.shade600, size: 32),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '语速',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '${pronunciation.speedWpm} 词/分钟',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.blue.shade700,
                ),
              ),
            ],
          ),
          const Spacer(),
          Text(
            _getSpeedLevel(pronunciation.speedWpm),
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Colors.blue.shade600,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建系统建议
  Widget _buildSuggestion() {
    String suggestion = _generateSuggestion();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.shade200, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb_outline, color: Colors.green.shade700),
              const SizedBox(width: 8),
              Text(
                '系统建议',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.green.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            suggestion,
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
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.shade300,
            blurRadius: 4,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: SizedBox(
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
              '关闭',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ============ 辅助方法 ============

  /// 获取分数颜色
  Color _getScoreColor(int score) {
    if (score >= 90) return Colors.green;
    if (score >= 80) return Colors.lightGreen.shade700;
    if (score >= 70) return Colors.orange;
    return Colors.deepOrange;
  }

  /// 获取单词状态颜色
  Color _getWordStatusColor(String status) {
    switch (status) {
      case 'good':
        return Colors.green;
      case 'needs_improvement':
        return Colors.orange;
      case 'bad':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  /// 获取单词状态图标
  IconData _getWordStatusIcon(String status) {
    switch (status) {
      case 'good':
        return Icons.check_circle;
      case 'needs_improvement':
        return Icons.warning;
      case 'bad':
        return Icons.cancel;
      default:
        return Icons.help;
    }
  }

  /// 获取语速等级
  String _getSpeedLevel(int wpm) {
    if (wpm >= 150) return '较快';
    if (wpm >= 120) return '正常';
    if (wpm >= 90) return '较慢';
    return '过慢';
  }

  /// 生成建议文本
  String _generateSuggestion() {
    final int score = pronunciation.score;
    final int problemWordsCount = pronunciation.problemWordsCount;

    if (score >= 95) {
      return '发音纯正，堪比母语者表达！继续保持这种优秀的发音水平。';
    } else if (score >= 85) {
      return '发音很好！${problemWordsCount > 0 ? "注意标记为待提高的单词发音" : "整体表现优秀"}，继续加油！';
    } else if (score >= 75) {
      return '发音良好，但还有提升空间。建议多练习标记为待提高的 $problemWordsCount 个单词，注意发音的准确性。';
    } else if (score >= 60) {
      return '发音需要改进。建议：1) 多听标准发音示例；2) 注意重点练习标记为错误的 $problemWordsCount 个单词；3) 适当放慢语速，提高清晰度。';
    } else {
      return '发音有较大提升空间。建议：1) 系统学习音标和发音规则；2) 每天跟读标准发音；3) 放慢语速，注重每个音节的准确性。加油！';
    }
  }
}
