// -*- coding: utf-8 -*-
/// 设置页面 - V1.4
/// 提供退出登录等设置功能
///
/// 功能：
/// - 显示设置项列表（动态从后端获取）
/// - 退出登录功能

import 'package:flutter/material.dart';
import '../services/user_service.dart';
import '../services/auth_service.dart';
import '../pages/auth/login_page.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final UserService _userService = UserService();
  final AuthService _authService = AuthService();

  /// 设置项数据
  Map<String, dynamic>? _settings;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  /// 加载设置项
  Future<void> _loadSettings() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final settings = await _userService.getUserSettings();

      setState(() {
        _settings = settings;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ 加载设置失败: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  /// 退出登录
  Future<void> _handleLogout() async {
    // 确认对话框
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('退出登录'),
        content: const Text('确定要退出登录吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('退出'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      // 显示加载
      if (!mounted) return;
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
      );

      // 调用后端退出登录接口
      await _userService.logout();

      // 清除本地认证信息
      await _authService.clearAuth();

      if (!mounted) return;

      // 关闭加载对话框
      Navigator.pop(context);

      // 跳转到登录页（清空导航栈）
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (context) => const LoginPage()),
        (route) => false,
      );

      print('✅ 退出登录成功');
    } catch (e) {
      print('❌ 退出登录失败: $e');

      if (!mounted) return;

      // 关闭加载对话框
      Navigator.pop(context);

      // 显示错误提示
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('退出登录失败: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black87),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          '设置',
          style: TextStyle(
            color: Colors.black87,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: true,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? _buildErrorView()
              : _buildSettingsContent(),
    );
  }

  /// 构建错误视图
  Widget _buildErrorView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          const Text(
            '加载失败',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.red,
            ),
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Text(
              _errorMessage!,
              style: const TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _loadSettings,
            child: const Text('重试'),
          ),
        ],
      ),
    );
  }

  /// 构建设置内容
  Widget _buildSettingsContent() {
    final logoutEnabled = _settings?['logout_enabled'] ?? true;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 退出登录按钮
          if (logoutEnabled)
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: InkWell(
                onTap: _handleLogout,
                borderRadius: BorderRadius.circular(16),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.logout,
                        color: Colors.red,
                        size: 24,
                      ),
                      const SizedBox(width: 16),
                      const Expanded(
                        child: Text(
                          '退出登录',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.red,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      const Icon(
                        Icons.chevron_right,
                        color: Colors.grey,
                        size: 24,
                      ),
                    ],
                  ),
                ),
              ),
            ),

          const SizedBox(height: 32),

          // 版本信息
          const Text(
            'PocketSpeak V1.4',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }
}
