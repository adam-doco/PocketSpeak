// 单词释义数据模型 - PocketSpeak V1.5.1
// 定义单词查询、音标、释义、生词本相关的数据结构

/// 单词释义项（V1.5.1新增）
class WordDefinitionItem {
  final String pos; // 词性（如：形容词、名词等）
  final String meaning; // 中文释义

  WordDefinitionItem({
    required this.pos,
    required this.meaning,
  });

  factory WordDefinitionItem.fromJson(Map<String, dynamic> json) {
    return WordDefinitionItem(
      pos: json['pos'] ?? '',
      meaning: json['meaning'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'pos': pos,
      'meaning': meaning,
    };
  }

  /// 格式化显示（词性. 释义）
  String get formatted => '$pos. $meaning';
}

/// 单词查询结果模型（V1.5.1：符合PRD要求）
class WordLookupResult {
  final String word;
  final String ukPhonetic; // 英式音标
  final String usPhonetic; // 美式音标
  final String ukAudioUrl; // 英式发音音频URL
  final String usAudioUrl; // 美式发音音频URL
  final List<WordDefinitionItem> definitions; // 释义列表
  final String mnemonic; // 联想记忆
  final String source; // 数据来源
  final String createdAt; // 创建时间

  WordLookupResult({
    required this.word,
    this.ukPhonetic = '',
    this.usPhonetic = '',
    this.ukAudioUrl = '',
    this.usAudioUrl = '',
    this.definitions = const [],
    this.mnemonic = '',
    this.source = '',
    this.createdAt = '',
  });

  factory WordLookupResult.fromJson(Map<String, dynamic> json) {
    return WordLookupResult(
      word: json['word'] ?? '',
      ukPhonetic: json['uk_phonetic'] ?? '',
      usPhonetic: json['us_phonetic'] ?? '',
      ukAudioUrl: json['uk_audio_url'] ?? '',
      usAudioUrl: json['us_audio_url'] ?? '',
      definitions: json['definitions'] != null
          ? (json['definitions'] as List)
              .map((item) => WordDefinitionItem.fromJson(item))
              .toList()
          : [],
      mnemonic: json['mnemonic'] ?? '',
      source: json['source'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'word': word,
      'uk_phonetic': ukPhonetic,
      'us_phonetic': usPhonetic,
      'uk_audio_url': ukAudioUrl,
      'us_audio_url': usAudioUrl,
      'definitions': definitions.map((d) => d.toJson()).toList(),
      'mnemonic': mnemonic,
      'source': source,
      'created_at': createdAt,
    };
  }

  /// 获取主要释义（用于生词本）
  String get mainDefinition {
    return definitions.isNotEmpty ? definitions[0].formatted : '';
  }

  /// 获取主要音标（优先美式）
  String get mainPhonetic {
    return usPhonetic.isNotEmpty ? usPhonetic : ukPhonetic;
  }
}

/// 生词收藏模型
class VocabFavorite {
  final String word;
  final String definition; // 主要释义（中文）
  final String phonetic; // 音标（美式优先）
  final String createdAt; // ISO格式时间字符串

  VocabFavorite({
    required this.word,
    required this.definition,
    required this.phonetic,
    required this.createdAt,
  });

  factory VocabFavorite.fromJson(Map<String, dynamic> json) {
    return VocabFavorite(
      word: json['word'] ?? '',
      definition: json['definition'] ?? '',
      phonetic: json['phonetic'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'word': word,
      'definition': definition,
      'phonetic': phonetic,
      'created_at': createdAt,
    };
  }

  /// 获取格式化的创建时间
  String get formattedDate {
    try {
      final date = DateTime.parse(createdAt);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    } catch (e) {
      return createdAt;
    }
  }
}

/// 生词本列表响应模型
class VocabListResponse {
  final bool success;
  final List<VocabFavorite> words;
  final int total;

  VocabListResponse({
    required this.success,
    required this.words,
    required this.total,
  });

  factory VocabListResponse.fromJson(Map<String, dynamic> json) {
    return VocabListResponse(
      success: json['success'] ?? false,
      words: json['words'] != null
          ? (json['words'] as List)
              .map((item) => VocabFavorite.fromJson(item))
              .toList()
          : [],
      total: json['total'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'success': success,
      'words': words.map((w) => w.toJson()).toList(),
      'total': total,
    };
  }
}
