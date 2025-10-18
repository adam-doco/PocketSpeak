import 'package:flutter/material.dart';
import 'pages/binding_page.dart';
import 'pages/chat_page.dart';
import 'pages/live2d_test_page.dart'; // Live2D测试页面
import 'pages/onboarding/welcome_page.dart'; // 欢迎页
import 'pages/auth/login_page.dart'; // V1.3: 登录页
import 'pages/main_page.dart'; // V1.4: 主页面（底部导航栏）
import 'services/api_service.dart';
import 'services/user_storage_service.dart'; // 用户存储服务
import 'services/auth_service.dart'; // V1.3: 认证服务

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
      // ✅ V1.3: 增加登录状态检查 + V1.2 用户引导流程检查
      home: FutureBuilder<Map<String, dynamic>>(
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
          final status = snapshot.data ?? {
            'isLoggedIn': false,
            'isActivated': false,
            'isOnboardingComplete': false
          };
          final isLoggedIn = status['isLoggedIn'] ?? false;
          final isActivated = status['isActivated'] ?? false;
          final isOnboardingComplete = status['isOnboardingComplete'] ?? false;

          // V1.4 + V1.3 + V1.2: 新的启动流程
          // 流程：登录检查 → 引导流程 → 主页面（底部导航栏）

          // 1. V1.3: 首先检查登录状态
          if (!isLoggedIn) {
            print('🔐 用户未登录，进入登录页面');
            return const LoginPage();
          }

          // 2. V1.2: 检查是否完成引导流程
          if (!isOnboardingComplete) {
            print('📝 已登录，但未完成引导流程，进入用户引导流程');
            return const WelcomePage();
          }

          // 3. V1.4: 全部完成，进入主页面（底部导航栏）
          print('✅ 用户已登录且已完成引导，进入主页面');
          return const MainPage();
        },
      ),
    );
  }

  /// V1.4 + V1.3 + V1.2: 检查应用状态（登录 + 用户引导）
  Future<Map<String, dynamic>> _checkAppStatus() async {
    try {
      // V1.3: 检查登录状态
      final authService = AuthService();
      final isLoggedIn = await authService.isLoggedIn();

      // 如果未登录，直接返回
      if (!isLoggedIn) {
        return {
          'isLoggedIn': false,
          'isOnboardingComplete': false,
          'isActivated': false,
        };
      }

      // V1.2: 检查用户引导流程
      final isOnboardingComplete = await UserStorageService.isOnboardingComplete();

      return {
        'isLoggedIn': true,
        'isOnboardingComplete': isOnboardingComplete,
        'isActivated': true, // V1.4: 不再需要设备激活流程
      };
    } catch (e) {
      print('❌ 检查应用状态失败: $e');
      // 出错时返回默认值（未登录）
      return {
        'isLoggedIn': false,
        'isOnboardingComplete': false,
        'isActivated': false,
      };
    }
  }
}

