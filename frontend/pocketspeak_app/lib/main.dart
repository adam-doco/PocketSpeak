import 'package:flutter/material.dart';
import 'pages/binding_page.dart';
import 'pages/chat_page.dart';
import 'services/api_service.dart';

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
      // ✅ 修复：根据设备激活状态显示不同页面
      home: FutureBuilder<bool>(
        future: _checkActivationStatus(),
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

          // ✅ 根据激活状态决定显示哪个页面
          final isActivated = snapshot.data ?? false;
          if (isActivated) {
            print('✅ 设备已激活，进入聊天页面');
            return const ChatPage();
          } else {
            print('⚠️ 设备未激活，进入激活页面');
            return const BindingPage();
          }
        },
      ),
    );
  }

  /// 检查设备激活状态
  Future<bool> _checkActivationStatus() async {
    try {
      final apiService = ApiService();
      final result = await apiService.waitForBindConfirmation();
      return result['is_activated'] ?? false;
    } catch (e) {
      print('❌ 检查激活状态失败: $e');
      // 出错时默认进入激活页面
      return false;
    }
  }
}

