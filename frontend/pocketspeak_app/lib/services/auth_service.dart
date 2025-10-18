// -*- coding: utf-8 -*-
/// 认证服务 - PocketSpeak V1.3
/// 处理用户登录、注册、Token 管理等功能

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// 认证服务类
class AuthService {
  // 单例模式
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  /// 后端 API 基础 URL
  static const String baseUrl = 'http://127.0.0.1:8000';

  /// Token 存储 Key
  static const String _tokenKey = 'auth_token';

  /// 用户信息存储 Key
  static const String _userInfoKey = 'user_info';

  /// 用户 ID 存储 Key (用于 V1.2 引导流程)
  static const String _userIdKey = 'current_user_id';

  /// 发送邮箱验证码
  ///
  /// Returns: 成功返回 true，失败返回 false 并抛出错误信息
  Future<bool> sendVerificationCode(String email) async {
    try {
      final url = Uri.parse('$baseUrl/api/auth/send-code');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return data['success'] ?? false;
      } else if (response.statusCode == 429) {
        // 发送频繁
        throw Exception(data['detail'] ?? '发送频繁，请稍后再试');
      } else {
        throw Exception(data['detail'] ?? '验证码发送失败');
      }
    } catch (e) {
      print('❌ 发送验证码失败: $e');
      rethrow;
    }
  }

  /// 邮箱验证码登录
  ///
  /// Returns: 登录成功返回用户信息，失败抛出异常
  Future<Map<String, dynamic>> loginWithEmailCode(
    String email,
    String code,
  ) async {
    try {
      final url = Uri.parse('$baseUrl/api/auth/login-code');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'code': code,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        if (data['success'] == true) {
          // 保存 Token
          final token = data['token'];
          await _saveToken(token);

          // 保存用户信息
          final user = data['user'];
          await _saveUserInfo(user);

          // ⭐ V1.3: 保存 user_id，供 V1.2 引导流程使用
          await _saveUserId(user['user_id']);

          print('✅ 登录成功: ${user['email']}');
          return user;
        } else {
          throw Exception('登录失败');
        }
      } else {
        throw Exception(data['detail'] ?? '验证码错误，请重试');
      }
    } catch (e) {
      print('❌ 登录失败: $e');
      rethrow;
    }
  }

  /// 获取当前登录用户信息
  ///
  /// 需要先登录获取 Token
  Future<Map<String, dynamic>?> getCurrentUser() async {
    try {
      final token = await getToken();
      if (token == null) {
        print('⚠️ 未登录，没有 Token');
        return null;
      }

      final url = Uri.parse('$baseUrl/api/user/me');
      final response = await http.get(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          final user = data['user'];
          await _saveUserInfo(user);
          return user;
        }
      } else if (response.statusCode == 401) {
        // Token 过期或无效
        print('⚠️ Token 无效，清除本地 Token');
        await clearAuth();
        return null;
      }

      return null;
    } catch (e) {
      print('❌ 获取当前用户失败: $e');
      return null;
    }
  }

  /// 登出
  Future<void> logout() async {
    try {
      final url = Uri.parse('$baseUrl/api/auth/logout');
      await http.post(url);
      print('👋 登出成功');
    } catch (e) {
      print('⚠️ 登出请求失败: $e');
    } finally {
      // 无论请求是否成功，都清除本地数据
      await clearAuth();
    }
  }

  /// 保存 Token 到本地
  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    print('💾 Token 已保存');
  }

  /// 获取本地 Token
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  /// 保存用户信息到本地
  Future<void> _saveUserInfo(Map<String, dynamic> userInfo) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userInfoKey, jsonEncode(userInfo));
    print('💾 用户信息已保存');
  }

  /// 获取本地用户信息
  Future<Map<String, dynamic>?> getUserInfo() async {
    final prefs = await SharedPreferences.getInstance();
    final userInfoStr = prefs.getString(_userInfoKey);
    if (userInfoStr != null) {
      return jsonDecode(userInfoStr);
    }
    return null;
  }

  /// 保存用户 ID 到本地 (用于 V1.2 引导流程)
  Future<void> _saveUserId(String userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userIdKey, userId);
    print('💾 用户 ID 已保存: $userId');
  }

  /// 获取当前登录用户的 ID
  Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userIdKey);
  }

  /// 清除所有认证信息
  Future<void> clearAuth() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userInfoKey);
    await prefs.remove(_userIdKey);
    print('🗑️ 认证信息已清除');
  }

  /// 检查是否已登录
  Future<bool> isLoggedIn() async {
    final token = await getToken();
    if (token == null) {
      return false;
    }

    // 验证 Token 是否有效（通过获取当前用户）
    final user = await getCurrentUser();
    return user != null;
  }

  /// 判断用户是否需要完成测评
  ///
  /// 如果用户没有 english_level，则需要跳转到测评页
  Future<bool> needsOnboarding() async {
    final userInfo = await getUserInfo();
    if (userInfo == null) {
      return true;
    }

    final englishLevel = userInfo['english_level'];
    return englishLevel == null;
  }
}
