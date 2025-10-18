// -*- coding: utf-8 -*-
/// 主页面 - V1.4
/// 底部导航栏容器，包含学习页和我的页两个Tab
///
/// 功能：
/// - 底部导航栏切换（学习、我的）
/// - 页面状态管理

import 'package:flutter/material.dart';
import 'learning_page.dart';
import 'profile_page.dart';

class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => _MainPageState();
}

class _MainPageState extends State<MainPage> {
  /// 当前选中的 Tab 索引
  int _currentIndex = 0;

  /// Tab 页面列表
  final List<Widget> _pages = [
    const LearningPage(),
    const ProfilePage(),
  ];

  /// 底部导航栏点击事件
  void _onTabTapped(int index) {
    setState(() {
      _currentIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: _onTabTapped,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: const Color(0xFF6C63FF),
        unselectedItemColor: Colors.grey,
        selectedFontSize: 12,
        unselectedFontSize: 12,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.school_outlined),
            activeIcon: Icon(Icons.school),
            label: '学习',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            activeIcon: Icon(Icons.person),
            label: '我的',
          ),
        ],
      ),
    );
  }
}
