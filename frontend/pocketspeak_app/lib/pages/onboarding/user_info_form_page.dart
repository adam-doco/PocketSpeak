import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import 'package:device_info_plus/device_info_plus.dart';
import '../../models/user_profile.dart';
import '../../services/user_storage_service.dart';
import '../../services/api_service.dart';
import 'onboarding_complete_page.dart';

/// 用户信息表单页
///
/// 收集用户的学习目标、英语水平、年龄段等信息
/// 包含三个问题：Q1-学习目的、Q2-英语水平、Q3-年龄段
class UserInfoFormPage extends StatefulWidget {
  const UserInfoFormPage({super.key});

  @override
  State<UserInfoFormPage> createState() => _UserInfoFormPageState();
}

class _UserInfoFormPageState extends State<UserInfoFormPage> {
  // 表单选择的值
  String? _selectedLearningGoal;
  String? _selectedEnglishLevel;
  String? _selectedAgeGroup;

  // 是否正在提交
  bool _isSubmitting = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, color: Color(0xFF667EEA)),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题
              const Text(
                '让我们了解一下你',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3436),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '帮助我们为你定制专属学习计划',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFF636E72),
                ),
              ),

              const SizedBox(height: 40),

              // Q1: 学习目的
              _buildQuestionSection(
                questionNumber: '1',
                question: '你练习英语口语的主要目的是什么？',
                child: _buildLearningGoalOptions(),
              ),

              const SizedBox(height: 32),

              // Q2: 英语水平
              _buildQuestionSection(
                questionNumber: '2',
                question: '你目前的英语水平如何？',
                child: _buildEnglishLevelOptions(),
              ),

              const SizedBox(height: 32),

              // Q3: 年龄段
              _buildQuestionSection(
                questionNumber: '3',
                question: '你目前的年龄段？',
                child: _buildAgeGroupOptions(),
              ),

              const SizedBox(height: 40),

              // 提交按钮
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _canSubmit ? _handleSubmit : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF667EEA),
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: const Color(0xFFDFE6E9),
                    disabledForegroundColor: const Color(0xFFB2BEC3),
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(28),
                    ),
                  ),
                  child: _isSubmitting
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text(
                          '开始学习',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建问题区域
  Widget _buildQuestionSection({
    required String questionNumber,
    required String question,
    required Widget child,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: const Color(0xFF667EEA).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Text(
                  questionNumber,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF667EEA),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                question,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D3436),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        child,
      ],
    );
  }

  /// 构建学习目标选项
  Widget _buildLearningGoalOptions() {
    return Column(
      children: LearningGoal.values.map((goal) {
        return _buildOptionTile(
          label: goal.label,
          value: goal.value,
          groupValue: _selectedLearningGoal,
          onTap: () {
            setState(() {
              _selectedLearningGoal = goal.value;
            });
          },
        );
      }).toList(),
    );
  }

  /// 构建英语水平选项
  Widget _buildEnglishLevelOptions() {
    return Column(
      children: EnglishLevel.values.map((level) {
        return _buildOptionTile(
          label: level.label,
          description: level.description,
          value: level.value,
          groupValue: _selectedEnglishLevel,
          onTap: () {
            setState(() {
              _selectedEnglishLevel = level.value;
            });
          },
        );
      }).toList(),
    );
  }

  /// 构建年龄段选项
  Widget _buildAgeGroupOptions() {
    return Column(
      children: AgeGroup.values.map((age) {
        return _buildOptionTile(
          label: age.label,
          value: age.value,
          groupValue: _selectedAgeGroup,
          onTap: () {
            setState(() {
              _selectedAgeGroup = age.value;
            });
          },
        );
      }).toList(),
    );
  }

  /// 构建单个选项
  Widget _buildOptionTile({
    required String label,
    String? description,
    required String value,
    required String? groupValue,
    required VoidCallback onTap,
  }) {
    final isSelected = value == groupValue;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF667EEA).withValues(alpha: 0.1) : const Color(0xFFF5F6FA),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? const Color(0xFF667EEA) : Colors.transparent,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isSelected ? const Color(0xFF667EEA) : const Color(0xFFB2BEC3),
                  width: 2,
                ),
                color: isSelected ? const Color(0xFF667EEA) : Colors.transparent,
              ),
              child: isSelected
                  ? const Icon(
                      Icons.check,
                      size: 14,
                      color: Colors.white,
                    )
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                      color: isSelected ? const Color(0xFF667EEA) : const Color(0xFF2D3436),
                    ),
                  ),
                  if (description != null && description.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: TextStyle(
                        fontSize: 13,
                        color: isSelected
                            ? const Color(0xFF667EEA).withValues(alpha: 0.7)
                            : const Color(0xFF636E72),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 检查是否可以提交
  bool get _canSubmit {
    return _selectedLearningGoal != null &&
        _selectedEnglishLevel != null &&
        _selectedAgeGroup != null &&
        !_isSubmitting;
  }

  /// 处理提交
  Future<void> _handleSubmit() async {
    if (!_canSubmit) return;

    setState(() {
      _isSubmitting = true;
    });

    try {
      // 生成 UUID
      const uuid = Uuid();
      final userId = uuid.v4();

      // 获取设备 ID
      final deviceId = await _getDeviceId();

      // 创建用户档案
      final userProfile = UserProfile(
        userId: userId,
        deviceId: deviceId,
        learningGoal: _selectedLearningGoal!,
        englishLevel: _selectedEnglishLevel!,
        ageGroup: _selectedAgeGroup!,
        createdAt: DateTime.now(),
        lastActive: DateTime.now(),
      );

      // 1. 保存到本地存储
      await UserStorageService.saveUserProfile(userProfile);
      // ignore: avoid_print
      print('✅ 用户档案已保存到本地存储');

      // 2. 同步到后端（V1.2）
      try {
        final apiService = ApiService();
        final result = await apiService.createUserProfile(
          userId: userProfile.userId,
          deviceId: userProfile.deviceId,
          learningGoal: userProfile.learningGoal,
          englishLevel: userProfile.englishLevel,
          ageGroup: userProfile.ageGroup,
        );

        if (result['success'] == true) {
          // ignore: avoid_print
          print('✅ 用户档案已同步到后端');
        } else {
          // ignore: avoid_print
          print('⚠️ 用户档案同步到后端失败: ${result['message']}');
          // 注意：即使后端同步失败，也不影响本地流程，继续进入完成页面
        }
      } catch (e) {
        // ignore: avoid_print
        print('⚠️ 用户档案同步到后端异常: $e');
        // 注意：即使后端同步失败，也不影响本地流程，继续进入完成页面
      }

      // 导航到完成页面
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (context) => const OnboardingCompletePage(),
          ),
        );
      }
    } catch (e) {
      // 显示错误提示
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('保存失败: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  /// 获取设备 ID
  Future<String> _getDeviceId() async {
    try {
      final deviceInfo = DeviceInfoPlugin();
      if (Theme.of(context).platform == TargetPlatform.iOS) {
        final iosInfo = await deviceInfo.iosInfo;
        return iosInfo.identifierForVendor ?? 'unknown_ios';
      } else if (Theme.of(context).platform == TargetPlatform.android) {
        final androidInfo = await deviceInfo.androidInfo;
        return androidInfo.id;
      } else {
        return 'unknown_device';
      }
    } catch (e) {
      return 'unknown_device';
    }
  }
}
