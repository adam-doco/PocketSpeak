// -*- coding: utf-8 -*-
/// 学习页面 - V1.4
/// 展示今日学习统计卡片和学习功能入口卡片
///
/// 功能：
/// - 显示今日学习时长、对话次数、跟读次数
/// - 提供自由对话和句子跟读入口

import 'package:flutter/material.dart';
import '../services/user_service.dart';
import '../widgets/learning_action_card.dart';
import 'chat_page.dart';

class LearningPage extends StatefulWidget {
  const LearningPage({super.key});

  @override
  State<LearningPage> createState() => _LearningPageState();
}

class _LearningPageState extends State<LearningPage> {
  final UserService _userService = UserService();

  /// 今日学习数据
  Map<String, dynamic>? _statsData;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  /// 加载今日学习统计
  Future<void> _loadStats() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final stats = await _userService.getUserStatsToday();

      setState(() {
        _statsData = stats;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ 加载学习统计失败: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          '学习',
          style: TextStyle(
            color: Colors.black87,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: _loadStats,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 今日学习统计卡片
              _buildStatsCard(),

              const SizedBox(height: 24),

              // 学习功能区标题
              const Text(
                '开始学习',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),

              const SizedBox(height: 16),

              // 自由对话卡片
              LearningActionCard(
                title: '自由对话',
                subtitle: '与 AI 自由交流，提升口语能力',
                icon: Icons.chat_bubble_outline,
                color: const Color(0xFF6C63FF),
                onTap: () {
                  // 跳转到 AI 聊天页面
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const ChatPage()),
                  );
                },
              ),

              const SizedBox(height: 12),

              // 句子跟读卡片
              LearningActionCard(
                title: '句子跟读',
                subtitle: '跟读经典句子，提高发音准确度',
                icon: Icons.mic_outlined,
                color: const Color(0xFFFF6B9D),
                onTap: () {
                  // TODO: 跳转到句子跟读页面
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('句子跟读功能开发中...')),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建今日学习统计卡片
  Widget _buildStatsCard() {
    if (_isLoading) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF6C63FF), Color(0xFF5A52D5)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
      );
    }

    if (_errorMessage != null) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 40),
            const SizedBox(height: 8),
            Text(
              '加载失败',
              style: TextStyle(
                color: Colors.red.shade700,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _errorMessage!,
              style: TextStyle(color: Colors.red.shade600, fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    final studyMinutes = _statsData?['study_minutes'] ?? 0;
    final freeTalkCount = _statsData?['free_talk_count'] ?? 0;
    final sentenceRepeatCount = _statsData?['sentence_repeat_count'] ?? 0;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF6C63FF), Color(0xFF5A52D5)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6C63FF).withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '今日学习',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatItem('学习时长', '$studyMinutes 分钟'),
              _buildStatItem('自由对话', '$freeTalkCount 次'),
              _buildStatItem('句子跟读', '$sentenceRepeatCount 次'),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建统计项
  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}
