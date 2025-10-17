import 'package:flutter/material.dart';
import 'pages/binding_page.dart';
import 'pages/chat_page.dart';
import 'pages/live2d_test_page.dart'; // Live2D测试页面
import 'pages/onboarding/welcome_page.dart'; // 欢迎页
import 'services/api_service.dart';
import 'services/user_storage_service.dart'; // 用户存储服务

void main() {
  runApp(const PocketSpeakApp());
}

class PocketSpeakApp extends StatelessWidget {
  const PocketSpeakApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PocketSpeak',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF667EEA),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'SF Pro Display',
      ),
      // 路由配置
      routes: {
        '/live2d_test': (context) => const Live2DTestPage(),
      },
      // ✅ V1.2: 增加用户引导流程检查
      home: FutureBuilder<Map<String, bool>>(
        future: _checkAppStatus(),
        builder: (context, snapshot) {
          // 加载中显示启动画面
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
              backgroundColor: Color(0xFF667EEA),
              body: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.mic,
                      size: 80,
                      color: Colors.white,
                    ),
                    SizedBox(height: 20),
                    Text(
                      'PocketSpeak',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 20),
                    CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  ],
                ),
              ),
            );
          }

          // ✅ 根据状态决定显示哪个页面
          final status = snapshot.data ?? {'isActivated': false, 'isOnboardingComplete': false};
          final isActivated = status['isActivated'] ?? false;
          final isOnboardingComplete = status['isOnboardingComplete'] ?? false;

          // V1.2: 新用户流程 - 优先完成引导流程
          // 流程：引导流程 → 设备激活 → 聊天页面

          // 1. 首先检查是否完成引导流程
          if (!isOnboardingComplete) {
            print('📝 新用户首次启动，进入用户引导流程');
            return const WelcomePage();
          }

          // 2. 引导完成后，检查设备激活状态
          if (!isActivated) {
            print('⚠️ 引导已完成，但设备未激活，进入激活页面');
            return const BindingPage();
          }

          // 3. 引导完成且设备已激活，进入主界面
          print('✅ 用户已完成引导且设备已激活，进入聊天页面');
          return const ChatPage();
        },
      ),
    );
  }

  /// V1.2: 检查应用状态（用户引导 + 设备激活）
  Future<Map<String, bool>> _checkAppStatus() async {
    try {
      // 检查用户引导流程
      final isOnboardingComplete = await UserStorageService.isOnboardingComplete();

      // 检查设备激活状态
      final apiService = ApiService();
      final result = await apiService.waitForBindConfirmation();
      final isActivated = result['is_activated'] ?? false;

      return {
        'isOnboardingComplete': isOnboardingComplete,
        'isActivated': isActivated,
      };
    } catch (e) {
      print('❌ 检查应用状态失败: $e');
      // 出错时返回默认值
      return {
        'isOnboardingComplete': false,
        'isActivated': false,
      };
    }
  }
}

