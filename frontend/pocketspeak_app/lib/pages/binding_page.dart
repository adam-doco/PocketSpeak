import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'chat_page.dart';

class BindingPage extends StatefulWidget {
  const BindingPage({super.key});

  @override
  State<BindingPage> createState() => _BindingPageState();
}

class _BindingPageState extends State<BindingPage>
    with TickerProviderStateMixin {
  String? deviceId;
  String? verifyCode;
  String bindingStatus = 'pending';
  bool isLoading = true;
  String? errorMessage;
  Timer? pollTimer;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _setupAnimation();
    _initializeBinding();
  }

  void _setupAnimation() {
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 0.95,
      end: 1.05,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    _pulseController.repeat(reverse: true);
  }

  Future<void> _initializeBinding() async {
    try {
      // 获取设备ID
      final deviceIdResult = await _apiService.getDeviceId();
      // 获取验证码
      final verifyCodeResult = await _apiService.getVerifyCode();

      setState(() {
        deviceId = deviceIdResult;
        verifyCode = verifyCodeResult;
        isLoading = false;
      });

      // 开始轮询绑定状态
      _startPolling();
    } catch (e) {
      setState(() {
        errorMessage = '初始化失败: $e';
        isLoading = false;
      });
    }
  }

  void _startPolling() {
    pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final status = await _apiService.checkBindStatus();
        if (mounted) {
          setState(() {
            bindingStatus = status ? 'success' : 'pending';
          });

          if (status) {
            timer.cancel();
            _navigateToChat();
          }
        }
      } catch (e) {
        if (mounted) {
          setState(() {
            bindingStatus = 'failed';
            errorMessage = '检查绑定状态失败: $e';
          });
        }
      }
    });
  }

  void _navigateToChat() {
    // 显示绑定成功弹窗
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF00B894).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.check_circle,
                  color: Color(0xFF00B894),
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '绑定成功',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3436),
                ),
              ),
            ],
          ),
          content: const Text(
            '您的设备已成功绑定到小智AI！现在可以开始英语学习之旅了。',
            style: TextStyle(
              fontSize: 14,
              color: Color(0xFF636E72),
              height: 1.5,
            ),
          ),
          actions: [
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.of(context).pop(); // 关闭弹窗
                  // 跳转到聊天页面
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (context) => const ChatPage()),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00B894),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  '开始聊天',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _refreshVerifyCode() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final newVerifyCode = await _apiService.getVerifyCode();
      setState(() {
        verifyCode = newVerifyCode;
        bindingStatus = 'pending';
        isLoading = false;
      });

      // 重新开始轮询
      pollTimer?.cancel();
      _startPolling();
    } catch (e) {
      setState(() {
        errorMessage = '刷新验证码失败: $e';
        isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    pollTimer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 获取屏幕尺寸
    final screenSize = MediaQuery.of(context).size;
    final screenWidth = screenSize.width;
    final screenHeight = screenSize.height;

    // 手机屏幕适配的内边距
    final horizontalPadding = screenWidth * 0.06; // 屏幕宽度的6%
    final verticalSpacing = screenHeight * 0.02; // 屏幕高度的2%

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(
            horizontal: horizontalPadding,
            vertical: verticalSpacing,
          ),
          child: Column(
            children: [
              SizedBox(height: verticalSpacing),
              _buildHeader(),
              SizedBox(height: verticalSpacing * 1.5),
              _buildMainContent(),
              SizedBox(height: verticalSpacing),
              if (bindingStatus == 'failed' || errorMessage != null)
                _buildRetryButton(),
              SizedBox(height: verticalSpacing), // 底部留白
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.1),
                blurRadius: 15,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Container(
              color: Colors.white,
              child: Image.asset(
                'assets/images/logo.png',
                width: 100,
                height: 100,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) {
                  // 如果图片加载失败，显示默认图标
                  return Container(
                    padding: const EdgeInsets.all(15),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF667EEA), Color(0xFF764BA2)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Icon(
                      Icons.psychology_outlined,
                      size: 55,
                      color: Colors.white,
                    ),
                  );
                },
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'PocketSpeak',
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: Color(0xFF2D3436),
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  Widget _buildMainContent() {
    if (isLoading) {
      return _buildLoadingState();
    }

    // 获取屏幕高度用于间距计算
    final screenHeight = MediaQuery.of(context).size.height;
    final verticalSpacing = screenHeight * 0.02;

    return Column(
      children: [
        _buildDeviceIdCard(),
        SizedBox(height: verticalSpacing),
        _buildVerifyCodeCard(),
        SizedBox(height: verticalSpacing),
        _buildInstructionCard(),
      ],
    );
  }

  Widget _buildLoadingState() {
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _pulseAnimation.value,
          child: Container(
            height: 120,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF74B9FF).withValues(alpha: 0.8),
                  const Color(0xFF0984E3).withValues(alpha: 0.8),
                ],
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                  SizedBox(height: 16),
                  Text(
                    '正在初始化...',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildDeviceIdCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF74B9FF).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.devices,
                  color: Color(0xFF74B9FF),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '设备ID',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3436),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF8F9FA),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: const Color(0xFFE9ECEF),
                width: 1,
              ),
            ),
            child: Text(
              deviceId ?? '获取中...',
              style: TextStyle(
                fontSize: 14,
                fontFamily: 'monospace',
                color: Colors.grey[700],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVerifyCodeCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF55A3FF), Color(0xFF003D82)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF55A3FF).withValues(alpha: 0.3),
            blurRadius: 15,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.key,
                color: Colors.white,
                size: 20,
              ),
              SizedBox(width: 6),
              Text(
                '验证码',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              verifyCode ?? '------',
              style: const TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2D3436),
                letterSpacing: 3,
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildInstructionCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFFFDCB6E).withValues(alpha: 0.1),
            const Color(0xFFE17055).withValues(alpha: 0.1),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFFDCB6E).withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFFDCB6E).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.info_outline,
                  color: Color(0xFFE17055),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '绑定说明',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3436),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            '请在小智 AI 官网输入上方验证码完成设备绑定',
            style: TextStyle(
              fontSize: 14,
              color: Color(0xFF636E72),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildRetryButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _refreshVerifyCode,
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF74B9FF),
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          elevation: 0,
        ),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.refresh, size: 20),
            SizedBox(width: 8),
            Text(
              '重新获取验证码',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

}