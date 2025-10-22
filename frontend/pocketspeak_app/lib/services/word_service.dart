// 单词查询服务 - PocketSpeak V1.5
// 调用后端API进行单词释义查询和生词本管理

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/word_definition.dart';
import '../services/auth_service.dart';

class WordService {
  // 基础URL - 与ApiService保持一致
  static const String baseUrl = 'http://localhost:8000';

  final AuthService _authService = AuthService();

  // V1.5: 单词查询缓存（减少API调用，提升响应速度）
  final Map<String, WordLookupResult> _wordCache = {};
  static const int _maxCacheSize = 100; // 最多缓存100个单词

  /// 查询单词释义
  ///
  /// Args:
  ///   word: 要查询的英文单词
  ///
  /// Returns:
  ///   WordLookupResult: 查询结果（包含音标、释义等）
  Future<WordLookupResult> lookupWord(String word) async {
    // V1.5: 检查缓存
    final cacheKey = word.toLowerCase();
    if (_wordCache.containsKey(cacheKey)) {
      print('✨ 从缓存获取单词: $word');
      return _wordCache[cacheKey]!;
    }

    try {
      print('🔍 查询单词: $word');

      final response = await http.get(
        Uri.parse('$baseUrl/api/words/lookup?word=${Uri.encodeComponent(word)}'),
        headers: {'Content-Type': 'application/json'},
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 查询成功: ${data['word']}');
        final result = WordLookupResult.fromJson(data);

        // V1.5.1: 只缓存完整且有效的结果
        // 条件：有音标内容, 有释义
        final hasValidPhonetic = result.usPhonetic.isNotEmpty || result.ukPhonetic.isNotEmpty;

        if (hasValidPhonetic && result.definitions.isNotEmpty) {
          _cacheWord(cacheKey, result);
          print('💾 数据完整，已缓存 - 音标: ${result.usPhonetic}/${result.ukPhonetic}, 释义数: ${result.definitions.length}');
        } else {
          print('⚠️ 数据不完整，不缓存:');
          print('   - US音标: "${result.usPhonetic}"');
          print('   - UK音标: "${result.ukPhonetic}"');
          print('   - 释义数: ${result.definitions.length}');
        }

        return result;
      } else if (response.statusCode == 400 || response.statusCode == 503) {
        // 业务错误（如词典服务未启用、查询失败等）
        final error = json.decode(response.body);
        print('❌ 查询失败: ${error['detail']}');
        throw Exception(error['detail'] ?? '查询失败');
      } else {
        throw Exception('查询失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 查询单词异常: $e');
      rethrow;
    }
  }

  /// 收藏单词到生词本
  ///
  /// Args:
  ///   word: 单词
  ///   definition: 释义（中文）
  ///   phonetic: 音标
  ///
  /// Returns:
  ///   Map: {success: bool, message: String}
  Future<Map<String, dynamic>> favoriteWord({
    required String word,
    required String definition,
    required String phonetic,
  }) async {
    try {
      print('⭐ 收藏单词: $word');

      // 获取认证token
      final token = await _authService.getToken();
      if (token == null) {
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      }

      final response = await http.post(
        Uri.parse('$baseUrl/api/words/favorite'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode({
          'word': word,
          'definition': definition,
          'phonetic': phonetic,
        }),
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 收藏成功: ${data['message']}');
        return {
          'success': data['success'] ?? true,
          'message': data['message'] ?? '收藏成功'
        };
      } else if (response.statusCode == 401) {
        print('❌ 未认证');
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      } else if (response.statusCode == 400) {
        final error = json.decode(response.body);
        print('⚠️ 收藏失败: ${error['detail']}');
        return {
          'success': false,
          'message': error['detail'] ?? '收藏失败'
        };
      } else {
        throw Exception('收藏失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 收藏单词异常: $e');
      return {
        'success': false,
        'message': '网络错误: $e'
      };
    }
  }

  /// 缓存单词查询结果
  void _cacheWord(String key, WordLookupResult result) {
    // 如果缓存已满，删除最早的条目（简单的FIFO策略）
    if (_wordCache.length >= _maxCacheSize) {
      final firstKey = _wordCache.keys.first;
      _wordCache.remove(firstKey);
      print('🗑️ 缓存已满，删除: $firstKey');
    }

    _wordCache[key] = result;
    print('💾 缓存单词: $key (总数: ${_wordCache.length})');
  }

  /// 获取生词本列表
  ///
  /// Returns:
  ///   VocabListResponse: 生词列表
  Future<VocabListResponse> getFavorites() async {
    try {
      print('📚 获取生词本列表');

      // 获取认证token
      final token = await _authService.getToken();
      if (token == null) {
        print('❌ 未登录');
        return VocabListResponse(
          success: false,
          words: [],
          total: 0,
        );
      }

      final response = await http.get(
        Uri.parse('$baseUrl/api/words/favorites'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 获取成功，共 ${data['total']} 个单词');
        return VocabListResponse.fromJson(data);
      } else if (response.statusCode == 401) {
        print('❌ 未认证');
        return VocabListResponse(
          success: false,
          words: [],
          total: 0,
        );
      } else {
        throw Exception('获取生词本失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 获取生词本异常: $e');
      return VocabListResponse(
        success: false,
        words: [],
        total: 0,
      );
    }
  }

  /// 删除生词
  ///
  /// Args:
  ///   word: 要删除的单词
  ///
  /// Returns:
  ///   Map: {success: bool, message: String}
  Future<Map<String, dynamic>> deleteFavorite(String word) async {
    try {
      print('🗑️ 删除生词: $word');

      // 获取认证token
      final token = await _authService.getToken();
      if (token == null) {
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      }

      final response = await http.delete(
        Uri.parse('$baseUrl/api/words/favorite/${Uri.encodeComponent(word)}'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 删除成功: ${data['message']}');
        return {
          'success': data['success'] ?? true,
          'message': data['message'] ?? '删除成功'
        };
      } else if (response.statusCode == 401) {
        print('❌ 未认证');
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      } else if (response.statusCode == 400) {
        final error = json.decode(response.body);
        print('⚠️ 删除失败: ${error['detail']}');
        return {
          'success': false,
          'message': error['detail'] ?? '删除失败'
        };
      } else {
        throw Exception('删除失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 删除生词异常: $e');
      return {
        'success': false,
        'message': '网络错误: $e'
      };
    }
  }

  /// 清空生词本
  ///
  /// Returns:
  ///   Map: {success: bool, message: String}
  Future<Map<String, dynamic>> clearFavorites() async {
    try {
      print('🗑️ 清空生词本');

      // 获取认证token
      final token = await _authService.getToken();
      if (token == null) {
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      }

      final response = await http.delete(
        Uri.parse('$baseUrl/api/words/favorites/clear'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 清空成功: ${data['message']}');
        return {
          'success': data['success'] ?? true,
          'message': data['message'] ?? '清空成功'
        };
      } else if (response.statusCode == 401) {
        print('❌ 未认证');
        return {
          'success': false,
          'message': '未登录，请先登录'
        };
      } else {
        throw Exception('清空失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 清空生词本异常: $e');
      return {
        'success': false,
        'message': '网络错误: $e'
      };
    }
  }
}
