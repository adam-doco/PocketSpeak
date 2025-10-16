/// Emoji识别器
///
/// 用于从AI返回的文本中提取emoji字符

class EmojiDetector {
  /// 从文本中提取第一个emoji
  ///
  /// 返回找到的第一个emoji字符，如果没有找到则返回null
  static String? extractFirstEmoji(String text) {
    if (text.isEmpty) return null;

    // Unicode emoji范围的正则表达式
    final emojiRegex = RegExp(
      r'[\u{1F600}-\u{1F64F}]|' // 表情符号 (Emoticons)
      r'[\u{1F300}-\u{1F5FF}]|' // 符号和象形文字 (Miscellaneous Symbols and Pictographs)
      r'[\u{1F680}-\u{1F6FF}]|' // 交通和地图符号 (Transport and Map Symbols)
      r'[\u{1F700}-\u{1F77F}]|' // 炼金术符号 (Alchemical Symbols)
      r'[\u{1F780}-\u{1F7FF}]|' // 几何形状扩展 (Geometric Shapes Extended)
      r'[\u{1F800}-\u{1F8FF}]|' // 补充箭头-C (Supplemental Arrows-C)
      r'[\u{1F900}-\u{1F9FF}]|' // 补充符号和象形文字 (Supplemental Symbols and Pictographs)
      r'[\u{1FA00}-\u{1FA6F}]|' // 象棋符号 (Chess Symbols)
      r'[\u{1FA70}-\u{1FAFF}]|' // 符号和象形文字扩展-A (Symbols and Pictographs Extended-A)
      r'[\u{2600}-\u{26FF}]|' // 杂项符号 (Miscellaneous Symbols)
      r'[\u{2700}-\u{27BF}]', // 装饰符号 (Dingbats)
      unicode: true,
    );

    final match = emojiRegex.firstMatch(text);
    return match?.group(0);
  }

  /// 提取文本中所有emoji
  ///
  /// 返回文本中所有emoji字符的列表
  static List<String> extractAllEmojis(String text) {
    if (text.isEmpty) return [];

    final emojiRegex = RegExp(
      r'[\u{1F600}-\u{1F64F}]|'
      r'[\u{1F300}-\u{1F5FF}]|'
      r'[\u{1F680}-\u{1F6FF}]|'
      r'[\u{1F700}-\u{1F77F}]|'
      r'[\u{1F780}-\u{1F7FF}]|'
      r'[\u{1F800}-\u{1F8FF}]|'
      r'[\u{1F900}-\u{1F9FF}]|'
      r'[\u{1FA00}-\u{1FA6F}]|'
      r'[\u{1FA70}-\u{1FAFF}]|'
      r'[\u{2600}-\u{26FF}]|'
      r'[\u{2700}-\u{27BF}]',
      unicode: true,
    );

    return emojiRegex
        .allMatches(text)
        .map((match) => match.group(0)!)
        .toList();
  }

  /// 检查文本是否包含emoji
  static bool containsEmoji(String text) {
    return extractFirstEmoji(text) != null;
  }

  /// 移除文本中的所有emoji
  ///
  /// 返回移除emoji后的纯文本
  static String removeEmojis(String text) {
    if (text.isEmpty) return text;

    final emojiRegex = RegExp(
      r'[\u{1F600}-\u{1F64F}]|'
      r'[\u{1F300}-\u{1F5FF}]|'
      r'[\u{1F680}-\u{1F6FF}]|'
      r'[\u{1F700}-\u{1F77F}]|'
      r'[\u{1F780}-\u{1F7FF}]|'
      r'[\u{1F800}-\u{1F8FF}]|'
      r'[\u{1F900}-\u{1F9FF}]|'
      r'[\u{1FA00}-\u{1FA6F}]|'
      r'[\u{1FA70}-\u{1FAFF}]|'
      r'[\u{2600}-\u{26FF}]|'
      r'[\u{2700}-\u{27BF}]',
      unicode: true,
    );

    return text.replaceAll(emojiRegex, '').trim();
  }
}
