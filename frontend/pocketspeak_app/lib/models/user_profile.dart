/// 用户档案数据模型
///
/// 用于存储用户的学习目标、英语水平、年龄段等基础信息
class UserProfile {
  final String userId;
  final String deviceId;
  final String learningGoal;
  final String englishLevel;
  final String ageGroup;
  final DateTime createdAt;
  final DateTime lastActive;

  UserProfile({
    required this.userId,
    required this.deviceId,
    required this.learningGoal,
    required this.englishLevel,
    required this.ageGroup,
    required this.createdAt,
    required this.lastActive,
  });

  /// 从 JSON 创建用户档案
  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      userId: json['user_id'] ?? '',
      deviceId: json['device_id'] ?? '',
      learningGoal: json['learning_goal'] ?? '',
      englishLevel: json['english_level'] ?? '',
      ageGroup: json['age_group'] ?? '',
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
      lastActive: DateTime.parse(json['last_active'] ?? DateTime.now().toIso8601String()),
    );
  }

  /// 转换为 JSON
  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'device_id': deviceId,
      'learning_goal': learningGoal,
      'english_level': englishLevel,
      'age_group': ageGroup,
      'created_at': createdAt.toIso8601String(),
      'last_active': lastActive.toIso8601String(),
    };
  }

  /// 复制并更新部分字段
  UserProfile copyWith({
    String? userId,
    String? deviceId,
    String? learningGoal,
    String? englishLevel,
    String? ageGroup,
    DateTime? createdAt,
    DateTime? lastActive,
  }) {
    return UserProfile(
      userId: userId ?? this.userId,
      deviceId: deviceId ?? this.deviceId,
      learningGoal: learningGoal ?? this.learningGoal,
      englishLevel: englishLevel ?? this.englishLevel,
      ageGroup: ageGroup ?? this.ageGroup,
      createdAt: createdAt ?? this.createdAt,
      lastActive: lastActive ?? this.lastActive,
    );
  }
}

/// 学习目标选项
enum LearningGoal {
  business('business', '商务职场英语'),
  exam('exam', '雅思/KET/PET'),
  daily('daily', '日常口语交流'),
  travel('travel', '出国旅游'),
  other('other', '其他');

  final String value;
  final String label;

  const LearningGoal(this.value, this.label);
}

/// 英语水平选项
enum EnglishLevel {
  a1('A1', 'A1 入门', '能运用最基础的语句'),
  a2('A2', 'A2 初级', '能简单交流讨论问题'),
  b1('B1', 'B1 中级', '可以轻松应对日常话题'),
  b2('B2', 'B2 中高', '全英文输出复杂观点'),
  c1('C1', 'C1 高级', '与外国人交流无障碍'),
  c2('C2', 'C2 专家', '如母语者般熟练'),
  uncertain('uncertain', '不太确定？测一测我的英语水平', '');

  final String value;
  final String label;
  final String description;

  const EnglishLevel(this.value, this.label, this.description);
}

/// 年龄段选项
enum AgeGroup {
  age12_20('12-20', '12-20岁'),
  age21_30('21-30', '21-30岁'),
  age31_40('31-40', '31-40岁'),
  age41_50('41-50', '41-50岁'),
  age51Plus('51+', '51岁以上');

  final String value;
  final String label;

  const AgeGroup(this.value, this.label);
}
