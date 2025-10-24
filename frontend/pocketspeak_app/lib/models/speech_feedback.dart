// 语音评分反馈数据模型 - PocketSpeak V1.6
// 定义语音评分相关的数据结构

/// 单词发音状态模型
class WordPronunciation {
  final String word; // 单词
  final String status; // 发音状态: "good", "bad", "needs_improvement"

  WordPronunciation({
    required this.word,
    required this.status,
  });

  factory WordPronunciation.fromJson(Map<String, dynamic> json) {
    return WordPronunciation(
      word: json['word'] ?? '',
      status: json['status'] ?? 'good',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'word': word,
      'status': status,
    };
  }

  /// 是否是好的发音
  bool get isGood => status == 'good';

  /// 是否是差的发音
  bool get isBad => status == 'bad';

  /// 是否需要改进
  bool get needsImprovement => status == 'needs_improvement';
}

/// 发音详细评分模型
class PronunciationDetail {
  final int score; // 总分 0-100
  final List<WordPronunciation> words; // 单词发音列表
  final int fluency; // 流利度 0-100
  final int clarity; // 清晰度 0-100
  final int completeness; // 完整度 0-100
  final int speedWpm; // 语速（词/分钟）

  PronunciationDetail({
    required this.score,
    required this.words,
    required this.fluency,
    required this.clarity,
    required this.completeness,
    required this.speedWpm,
  });

  factory PronunciationDetail.fromJson(Map<String, dynamic> json) {
    return PronunciationDetail(
      score: json['score'] ?? 0,
      words: json['words'] != null
          ? (json['words'] as List)
              .map((item) => WordPronunciation.fromJson(item))
              .toList()
          : [],
      fluency: json['fluency'] ?? 0,
      clarity: json['clarity'] ?? 0,
      completeness: json['completeness'] ?? 0,
      speedWpm: json['speed_wpm'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'score': score,
      'words': words.map((w) => w.toJson()).toList(),
      'fluency': fluency,
      'clarity': clarity,
      'completeness': completeness,
      'speed_wpm': speedWpm,
    };
  }

  /// 获取问题单词数量
  int get problemWordsCount {
    return words.where((w) => w.isBad || w.needsImprovement).length;
  }

  /// 获取正确单词数量
  int get correctWordsCount {
    return words.where((w) => w.isGood).length;
  }
}

/// 语法分析模型
class GrammarAnalysis {
  final bool hasError; // 是否有语法错误
  final String original; // 原始句子
  final String? suggestion; // 修改建议（如果有错误）
  final String? reason; // 错误原因说明

  GrammarAnalysis({
    required this.hasError,
    required this.original,
    this.suggestion,
    this.reason,
  });

  factory GrammarAnalysis.fromJson(Map<String, dynamic> json) {
    return GrammarAnalysis(
      hasError: json['has_error'] ?? false,
      original: json['original'] ?? '',
      suggestion: json['suggestion'],
      reason: json['reason'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'has_error': hasError,
      'original': original,
      'suggestion': suggestion,
      'reason': reason,
    };
  }
}

/// 表达评估模型
class ExpressionEvaluation {
  final String level; // 地道程度等级: "不地道", "一般", "地道", "非常地道"
  final String? suggestion; // 优化建议（如果有）
  final String? reason; // 建议原因说明

  ExpressionEvaluation({
    required this.level,
    this.suggestion,
    this.reason,
  });

  factory ExpressionEvaluation.fromJson(Map<String, dynamic> json) {
    return ExpressionEvaluation(
      level: json['level'] ?? '一般',
      suggestion: json['suggestion'],
      reason: json['reason'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'level': level,
      'suggestion': suggestion,
      'reason': reason,
    };
  }

  /// 是否需要优化
  bool get needsImprovement => level == '不地道' || level == '一般';

  /// 是否地道
  bool get isNative => level == '地道' || level == '非常地道';
}

/// 语音评分反馈响应模型
class SpeechFeedbackResponse {
  final int overallScore; // 综合得分 0-100
  final GrammarAnalysis grammar; // 语法分析
  final PronunciationDetail pronunciation; // 发音详情
  final ExpressionEvaluation expression; // 表达评估
  final String createdAt; // 创建时间

  SpeechFeedbackResponse({
    required this.overallScore,
    required this.grammar,
    required this.pronunciation,
    required this.expression,
    required this.createdAt,
  });

  factory SpeechFeedbackResponse.fromJson(Map<String, dynamic> json) {
    return SpeechFeedbackResponse(
      overallScore: json['overall_score'] ?? 0,
      grammar: GrammarAnalysis.fromJson(json['grammar'] ?? {}),
      pronunciation: PronunciationDetail.fromJson(json['pronunciation'] ?? {}),
      expression: ExpressionEvaluation.fromJson(json['expression'] ?? {}),
      createdAt: json['created_at'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'overall_score': overallScore,
      'grammar': grammar.toJson(),
      'pronunciation': pronunciation.toJson(),
      'expression': expression.toJson(),
      'created_at': createdAt,
    };
  }

  /// 获取评分等级文字
  String get scoreLevel {
    if (overallScore >= 90) return '优秀';
    if (overallScore >= 80) return '良好';
    if (overallScore >= 70) return '中等';
    if (overallScore >= 60) return '及格';
    return '需努力';
  }

  /// 获取评分等级颜色
  /// 返回Material颜色值（需要在UI层转换）
  String get scoreLevelColor {
    if (overallScore >= 90) return 'green';
    if (overallScore >= 80) return 'lightGreen';
    if (overallScore >= 70) return 'orange';
    if (overallScore >= 60) return 'deepOrange';
    return 'red';
  }
}
