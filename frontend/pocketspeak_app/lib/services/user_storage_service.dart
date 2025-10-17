import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_profile.dart';

/// 用户数据本地存储服务
///
/// 使用 SharedPreferences 存储用户档案信息
/// 提供保存、读取、删除等基础操作
class UserStorageService {
  static const String _userProfileKey = 'user_profile';
  static const String _onboardingCompleteKey = 'onboarding_complete';

  /// 保存用户档案
  static Future<void> saveUserProfile(UserProfile profile) async {
    final prefs = await SharedPreferences.getInstance();
    final json = jsonEncode(profile.toJson());
    await prefs.setString(_userProfileKey, json);
    await prefs.setBool(_onboardingCompleteKey, true);
  }

  /// 获取用户档案
  static Future<UserProfile?> getUserProfile() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final json = prefs.getString(_userProfileKey);

      if (json == null) return null;

      final map = jsonDecode(json) as Map<String, dynamic>;
      return UserProfile.fromJson(map);
    } catch (e) {
      // ignore: avoid_print
      print('获取用户档案失败: $e');
      return null;
    }
  }

  /// 检查是否完成引导流程
  static Future<bool> isOnboardingComplete() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_onboardingCompleteKey) ?? false;
  }

  /// 更新用户最后活跃时间
  static Future<void> updateLastActive() async {
    final profile = await getUserProfile();
    if (profile != null) {
      final updatedProfile = profile.copyWith(
        lastActive: DateTime.now(),
      );
      await saveUserProfile(updatedProfile);
    }
  }

  /// 清除用户数据（用于测试或退出登录）
  static Future<void> clearUserData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userProfileKey);
    await prefs.remove(_onboardingCompleteKey);
  }
}
