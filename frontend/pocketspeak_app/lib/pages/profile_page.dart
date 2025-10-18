// -*- coding: utf-8 -*-
/// 我的页面 - V1.4
/// 展示用户头像、昵称、等级、设置入口
///
/// 功能：
/// - 显示用户基本信息（头像、昵称、邮箱、等级）
/// - 提供设置页面入口

import 'package:flutter/material.dart';
import '../services/user_service.dart';
import 'settings_page.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final UserService _userService = UserService();

  /// 用户信息数据
  Map<String, dynamic>? _userInfo;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadUserInfo();
  }

  /// 加载用户信息
  Future<void> _loadUserInfo() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final userInfo = await _userService.getUserInfo();

      setState(() {
        _userInfo = userInfo;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ 加载用户信息失败: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          '我的',
          style: TextStyle(
            color: Colors.black87,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: true,
        actions: [
          // 设置按钮
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: Colors.black87),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsPage()),
              );
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadUserInfo,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? _buildErrorView()
                : _buildProfileContent(),
      ),
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
          Text(
            '加载失败',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.red.shade700,
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
            onPressed: _loadUserInfo,
            child: const Text('重试'),
          ),
        ],
      ),
    );
  }

  /// 构建个人资料内容
  Widget _buildProfileContent() {
    final nickname = _userInfo?['nickname'] ?? '用户';
    final email = _userInfo?['email'] ?? '';
    final level = _userInfo?['level'] ?? '';
    final levelLabel = _userInfo?['level_label'] ?? '';
    final avatarUrl = _userInfo?['avatar_url'];

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        children: [
          // 用户信息卡片
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            margin: const EdgeInsets.all(16),
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
            child: Column(
              children: [
                // 头像
                CircleAvatar(
                  radius: 50,
                  backgroundColor: const Color(0xFF6C63FF).withOpacity(0.1),
                  backgroundImage:
                      avatarUrl != null ? NetworkImage(avatarUrl) : null,
                  child: avatarUrl == null
                      ? const Icon(
                          Icons.person,
                          size: 50,
                          color: Color(0xFF6C63FF),
                        )
                      : null,
                ),

                const SizedBox(height: 16),

                // 昵称
                Text(
                  nickname,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.black87,
                  ),
                ),

                const SizedBox(height: 8),

                // 邮箱
                if (email.isNotEmpty)
                  Text(
                    email,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.grey,
                    ),
                  ),

                const SizedBox(height: 16),

                // 等级标签
                if (level.isNotEmpty)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6C63FF), Color(0xFF5A52D5)],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.star,
                          color: Colors.white,
                          size: 16,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '$level · $levelLabel',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // 功能菜单列表
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
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
            child: Column(
              children: [
                _buildMenuItem(
                  icon: Icons.account_circle_outlined,
                  title: '账号管理',
                  onTap: () {
                    // TODO: 跳转到账号管理页面
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('账号管理功能开发中...')),
                    );
                  },
                ),
                const Divider(height: 1),
                _buildMenuItem(
                  icon: Icons.description_outlined,
                  title: '用户协议',
                  onTap: () {
                    // TODO: 跳转到用户协议页面
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('用户协议功能开发中...')),
                    );
                  },
                ),
                const Divider(height: 1),
                _buildMenuItem(
                  icon: Icons.privacy_tip_outlined,
                  title: '隐私政策',
                  onTap: () {
                    // TODO: 跳转到隐私政策页面
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('隐私政策功能开发中...')),
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  /// 构建菜单项
  Widget _buildMenuItem({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          children: [
            Icon(icon, color: Colors.black87, size: 24),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  color: Colors.black87,
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
    );
  }
}
