// -*- coding: utf-8 -*-
/// 学习功能卡片组件 - V1.4
/// 用于学习页面的功能入口卡片
///
/// 功能：
/// - 展示学习功能的图标、标题、副标题
/// - 点击跳转到对应功能页面

import 'package:flutter/material.dart';

class LearningActionCard extends StatelessWidget {
  /// 卡片标题
  final String title;

  /// 卡片副标题
  final String subtitle;

  /// 卡片图标
  final IconData icon;

  /// 卡片主色调
  final Color color;

  /// 点击事件
  final VoidCallback onTap;

  const LearningActionCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: color.withOpacity(0.2),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.1),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            // 图标
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: color,
                size: 28,
              ),
            ),

            const SizedBox(width: 16),

            // 文字内容
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.black87,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
            ),

            // 箭头图标
            Icon(
              Icons.arrow_forward_ios,
              color: color.withOpacity(0.5),
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}
