// -*- coding: utf-8 -*-
/// 用户服务 - V1.4
/// 提供用户信息、学习统计、设置等接口调用
///
/// 功能：
/// - 获取用户基础信息（昵称、头像、等级）
/// - 获取今日学习统计数据
/// - 获取用户设置项
/// - 用户退出登录

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class UserService {
  /// API 基础 URL（根据环境配置）
  static const String _baseUrl = 'http://127.0.0.1:8000';

  /// Token 存储 Key
  static const String _tokenKey = 'auth_token';

  /// 获取存储的 Token
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  /// 获取用户基础信息
  ///
  /// Returns:
  ///   Map<String, dynamic>: {
  ///     "user_id": "u123456",
  ///     "nickname": "Alex",
  ///     "avatar_url": "https://...",
  ///     "email": "alex@example.com",
  ///     "level": "B1",
  ///     "level_label": "中级"
  ///   }
  ///
  /// Throws:
  ///   Exception: 网络错误或认证失败
  Future<Map<String, dynamic>> getUserInfo() async {
    print('\n📋 请求获取用户信息...');

    final token = await _getToken();
    if (token == null) {
      throw Exception('未登录，请先登录');
    }

    final url = Uri.parse('$_baseUrl/api/user/info');
    final response = await http.get(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    print('📡 响应状态码: ${response.statusCode}');

    if (response.statusCode == 200) {
      final data = json.decode(utf8.decode(response.bodyBytes));
      print('✅ 用户信息获取成功');
      return data;
    } else if (response.statusCode == 401) {
      throw Exception('认证失败，请重新登录');
    } else {
      final error = json.decode(utf8.decode(response.bodyBytes));
      throw Exception(error['detail'] ?? '获取用户信息失败');
    }
  }

  /// 获取今日学习统计数据
  ///
  /// Returns:
  ///   Map<String, dynamic>: {
  ///     "date": "2025-10-19",
  ///     "study_minutes": 42,
  ///     "free_talk_count": 3,
  ///     "sentence_repeat_count": 5
  ///   }
  ///
  /// Throws:
  ///   Exception: 网络错误或认证失败
  Future<Map<String, dynamic>> getUserStatsToday() async {
    print('\n📊 请求获取今日学习统计...');

    final token = await _getToken();
    if (token == null) {
      throw Exception('未登录，请先登录');
    }

    final url = Uri.parse('$_baseUrl/api/user/stats/today');
    final response = await http.get(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    print('📡 响应状态码: ${response.statusCode}');

    if (response.statusCode == 200) {
      final data = json.decode(utf8.decode(response.bodyBytes));
      print('✅ 学习统计获取成功');
      return data;
    } else if (response.statusCode == 401) {
      throw Exception('认证失败，请重新登录');
    } else {
      final error = json.decode(utf8.decode(response.bodyBytes));
      throw Exception(error['detail'] ?? '获取学习统计失败');
    }
  }

  /// 获取用户设置项
  ///
  /// Returns:
  ///   Map<String, dynamic>: {
  ///     "account_enabled": true,
  ///     "show_terms": true,
  ///     "show_privacy": true,
  ///     "logout_enabled": true
  ///   }
  ///
  /// Throws:
  ///   Exception: 网络错误或认证失败
  Future<Map<String, dynamic>> getUserSettings() async {
    print('\n⚙️  请求获取用户设置...');

    final token = await _getToken();
    if (token == null) {
      throw Exception('未登录，请先登录');
    }

    final url = Uri.parse('$_baseUrl/api/user/settings');
    final response = await http.get(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    print('📡 响应状态码: ${response.statusCode}');

    if (response.statusCode == 200) {
      final data = json.decode(utf8.decode(response.bodyBytes));
      print('✅ 用户设置获取成功');
      return data;
    } else if (response.statusCode == 401) {
      throw Exception('认证失败，请重新登录');
    } else {
      final error = json.decode(utf8.decode(response.bodyBytes));
      throw Exception(error['detail'] ?? '获取用户设置失败');
    }
  }

  /// 用户退出登录
  ///
  /// Returns:
  ///   Map<String, dynamic>: {
  ///     "success": true,
  ///     "message": "退出登录成功"
  ///   }
  ///
  /// Throws:
  ///   Exception: 网络错误或认证失败
  Future<Map<String, dynamic>> logout() async {
    print('\n👋 请求退出登录...');

    final token = await _getToken();
    if (token == null) {
      throw Exception('未登录');
    }

    final url = Uri.parse('$_baseUrl/api/user/logout');
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    print('📡 响应状态码: ${response.statusCode}');

    if (response.statusCode == 200) {
      final data = json.decode(utf8.decode(response.bodyBytes));
      print('✅ 退出登录成功');

      // 清除本地 Token
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_tokenKey);
      print('🗑️  本地 Token 已清除');

      return data;
    } else if (response.statusCode == 401) {
      throw Exception('认证失败');
    } else {
      final error = json.decode(utf8.decode(response.bodyBytes));
      throw Exception(error['detail'] ?? '退出登录失败');
    }
  }
}
