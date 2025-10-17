import 'package:flutter/material.dart';
import '../chat_page.dart';
import '../../services/user_storage_service.dart';

/// 引导流程完成页
///
/// 用户提交信息后显示，提示"你的英语AI助手已准备好"
/// 点击按钮进入主聊天界面
class OnboardingCompletePage extends StatefulWidget {
  const OnboardingCompletePage({super.key});

  @override
  State<OnboardingCompletePage> createState() => _OnboardingCompletePageState();
}

class _OnboardingCompletePageState extends State<OnboardingCompletePage> {
  @override
  void initState() {
    super.initState();
    _logUserProfile();
  }

  /// 记录用户档案信息到控制台（用于调试）
  Future<void> _logUserProfile() async {
    final profile = await UserStorageService.getUserProfile();
    if (profile != null) {
      // ignore: avoid_print
      print('📝 用户引导流程完成');
      // ignore: avoid_print
      print('   User ID: ${profile.userId}');
      // ignore: avoid_print
      print('   Device ID: ${profile.deviceId}');
      // ignore: avoid_print
      print('   学习目标: ${profile.learningGoal}');
      // ignore: avoid_print
      print('   英语水平: ${profile.englishLevel}');
      // ignore: avoid_print
      print('   年龄段: ${profile.ageGroup}');
      // ignore: avoid_print
      print('   创建时间: ${profile.createdAt}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFF667EEA),
              Color(0xFF764BA2),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(flex: 2),

              // 成功图标
              Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_circle_outline,
                  size: 60,
                  color: Colors.white,
                ),
              ),

              const SizedBox(height: 40),

              // 成功提示
              const Text(
                '准备就绪！',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),

              const SizedBox(height: 16),

              // 描述文字
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  '你的英语AI助手已准备好\n让我们开始练习英语口语吧',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white,
                    height: 1.5,
                  ),
                ),
              ),

              const Spacer(flex: 3),

              // 开始对话按钮
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pushAndRemoveUntil(
                        MaterialPageRoute(
                          builder: (context) => const ChatPage(),
                        ),
                        (route) => false, // 清除所有之前的路由
                      );
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF667EEA),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(28),
                      ),
                    ),
                    child: const Text(
                      '开始对话',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 60),
            ],
          ),
        ),
      ),
    );
  }
}
