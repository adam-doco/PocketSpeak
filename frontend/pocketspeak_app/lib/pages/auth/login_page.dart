// -*- coding: utf-8 -*-
/// 登录页面 - PocketSpeak V1.3
/// 支持邮箱验证码登录和 Apple ID 登录（预留）

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';

import '../../services/auth_service.dart';
import '../onboarding/welcome_page.dart';
import '../main_page.dart';

/// 登录页面
class LoginPage extends StatefulWidget {
  const LoginPage({Key? key}) : super(key: key);

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  // 认证服务
  final AuthService _authService = AuthService();

  // 表单控制器
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _codeController = TextEditingController();

  // 表单 Key
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  // 状态管理
  bool _isLoading = false;
  bool _isSendingCode = false;
  int _countdown = 0;
  Timer? _countdownTimer;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _countdownTimer?.cancel();
    super.dispose();
  }

  /// 验证邮箱格式
  bool _isValidEmail(String email) {
    final emailRegex = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');
    return emailRegex.hasMatch(email);
  }

  /// 发送验证码
  Future<void> _sendVerificationCode() async {
    // 验证邮箱
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      setState(() {
        _errorMessage = '请输入邮箱地址';
      });
      return;
    }

    if (!_isValidEmail(email)) {
      setState(() {
        _errorMessage = '邮箱格式不正确';
      });
      return;
    }

    setState(() {
      _isSendingCode = true;
      _errorMessage = null;
    });

    try {
      await _authService.sendVerificationCode(email);

      // 启动倒计时
      setState(() {
        _countdown = 60;
        _isSendingCode = false;
      });

      _countdownTimer?.cancel();
      _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        setState(() {
          if (_countdown > 0) {
            _countdown--;
          } else {
            timer.cancel();
          }
        });
      });

      // 显示成功提示
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('验证码已发送，请查收'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isSendingCode = false;
        _errorMessage = e.toString().replaceAll('Exception: ', '');
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage!),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// 登录
  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final email = _emailController.text.trim();
    final code = _codeController.text.trim();

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // 调用登录接口
      final user = await _authService.loginWithEmailCode(email, code);

      print('✅ 登录成功: ${user['email']}');

      // 判断是否需要完成测评
      final needsOnboarding = user['english_level'] == null;

      if (mounted) {
        if (needsOnboarding) {
          // 跳转到测评页（V1.2 新用户）
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => const WelcomePage(),
            ),
          );
        } else {
          // 跳转到主页（V1.4 已注册用户）
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => const MainPage(),
            ),
          );
        }
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceAll('Exception: ', '');
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage!),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 60),

                // Logo 和标题
                Center(
                  child: Column(
                    children: [
                      // Logo
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: Colors.blue.shade100,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Icon(
                          Icons.chat_bubble_outline,
                          size: 40,
                          color: Colors.blue,
                        ),
                      ),
                      const SizedBox(height: 24),

                      // 欢迎标题
                      const Text(
                        '欢迎使用 PocketSpeak',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        '用AI开启英语口语学习之旅',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.black54,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 48),

                // 邮箱输入框
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: '邮箱地址',
                    hintText: '请输入邮箱地址',
                    prefixIcon: const Icon(Icons.email_outlined),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: Colors.grey.shade50,
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return '请输入邮箱地址';
                    }
                    if (!_isValidEmail(value.trim())) {
                      return '邮箱格式不正确';
                    }
                    return null;
                  },
                ),

                const SizedBox(height: 16),

                // 验证码输入框 + 获取验证码按钮
                Row(
                  children: [
                    // 验证码输入框
                    Expanded(
                      child: TextFormField(
                        controller: _codeController,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                        ],
                        decoration: InputDecoration(
                          labelText: '验证码',
                          hintText: '6位数字验证码',
                          prefixIcon: const Icon(Icons.lock_outline),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          filled: true,
                          fillColor: Colors.grey.shade50,
                          counterText: '',
                        ),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入验证码';
                          }
                          if (value.trim().length != 6) {
                            return '验证码为6位数字';
                          }
                          return null;
                        },
                      ),
                    ),

                    const SizedBox(width: 12),

                    // 获取验证码按钮
                    SizedBox(
                      width: 120,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: _countdown > 0 || _isSendingCode
                            ? null
                            : _sendVerificationCode,
                        style: ElevatedButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: _isSendingCode
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    Colors.white,
                                  ),
                                ),
                              )
                            : Text(
                                _countdown > 0 ? '$_countdown 秒' : '获取验证码',
                                style: const TextStyle(fontSize: 14),
                              ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // 登录按钮
                SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _login,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          )
                        : const Text(
                            '登录',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                  ),
                ),

                const SizedBox(height: 24),

                // 分割线
                const Row(
                  children: [
                    Expanded(child: Divider()),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16),
                      child: Text(
                        '或',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ),
                    Expanded(child: Divider()),
                  ],
                ),

                const SizedBox(height: 24),

                // Apple 登录按钮（预留）
                SizedBox(
                  height: 56,
                  child: OutlinedButton.icon(
                    onPressed: null, // 暂未实现
                    icon: const Icon(Icons.apple, size: 24),
                    label: const Text('使用 Apple 登录'),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 32),

                // 条款提示
                Center(
                  child: Text.rich(
                    TextSpan(
                      text: '登录即代表同意',
                      style: const TextStyle(
                        color: Colors.grey,
                        fontSize: 12,
                      ),
                      children: [
                        TextSpan(
                          text: '《服务条款》',
                          style: TextStyle(
                            color: Colors.blue.shade700,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                        const TextSpan(text: '和'),
                        TextSpan(
                          text: '《隐私政策》',
                          style: TextStyle(
                            color: Colors.blue.shade700,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ],
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),

                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
