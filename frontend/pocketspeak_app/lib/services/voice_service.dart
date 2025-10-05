import 'dart:convert';
import 'package:http/http.dart' as http;

/// 语音交互服务
/// 封装与后端语音API的所有交互
class VoiceService {
  static const String baseUrl = 'http://localhost:8000';

  // 会话状态
  bool _isSessionInitialized = false;
  String? _sessionId;
  String? _currentState;

  // 获取会话初始化状态
  bool get isSessionInitialized => _isSessionInitialized;
  String? get sessionId => _sessionId;
  String? get currentState => _currentState;

  // ============== 会话管理 ==============

  /// 初始化语音会话
  Future<Map<String, dynamic>> initSession({
    bool autoPlayTts = false,  // 前端播放音频,后端不播放
    bool saveConversation = true,
    bool enableEchoCancellation = true,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/session/init'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'auto_play_tts': autoPlayTts,
          'save_conversation': saveConversation,
          'enable_echo_cancellation': enableEchoCancellation,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          _isSessionInitialized = true;
          _sessionId = data['data']?['session_id'];
          _currentState = data['data']?['state'];

          print('✅ 语音会话初始化成功: $_sessionId');
          return {
            'success': true,
            'message': data['message'] ?? '语音会话初始化成功',
            'session_id': _sessionId,
            'state': _currentState,
            'data': data['data'] ?? {},
          };
        } else {
          return {
            'success': false,
            'message': data['message'] ?? '初始化失败',
            'data': data['data'] ?? {},
          };
        }
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '初始化语音会话失败',
          'data': errorData['detail']?['data'] ?? {},
        };
      }
    } catch (e) {
      print('❌ 初始化语音会话异常: $e');
      return {
        'success': false,
        'message': '初始化语音会话失败: $e',
        'data': {},
      };
    }
  }

  /// 关闭语音会话
  Future<Map<String, dynamic>> closeSession() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/session/close'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        _isSessionInitialized = false;
        _sessionId = null;
        _currentState = null;

        print('✅ 语音会话已关闭');
        return {
          'success': data['success'] ?? true,
          'message': data['message'] ?? '语音会话已关闭',
          'data': data['data'] ?? {},
        };
      } else {
        throw Exception('关闭语音会话失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 关闭语音会话异常: $e');
      return {
        'success': false,
        'message': '关闭语音会话失败: $e',
        'data': {},
      };
    }
  }

  /// 获取会话状态
  Future<Map<String, dynamic>> getSessionStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/voice/session/status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['success'] == true) {
          _isSessionInitialized = data['data']?['initialized'] ?? false;
          _sessionId = data['data']?['session_id'];
          _currentState = data['data']?['state'];
        }

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'data': data['data'] ?? {},
        };
      } else {
        throw Exception('获取会话状态失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 获取会话状态异常: $e');
      return {
        'success': false,
        'message': '获取会话状态失败: $e',
        'data': {'initialized': false},
      };
    }
  }

  // ============== 录音控制 ==============

  /// 开始录音
  Future<Map<String, dynamic>> startRecording() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/recording/start'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['success'] == true) {
          _currentState = data['data']?['state'];
          print('🎤 开始录音');
        }

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'state': data['data']?['state'],
          'is_recording': data['data']?['is_recording'] ?? false,
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '开始录音失败',
        };
      }
    } catch (e) {
      print('❌ 开始录音异常: $e');
      return {
        'success': false,
        'message': '开始录音失败: $e',
      };
    }
  }

  /// 停止录音
  Future<Map<String, dynamic>> stopRecording() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/recording/stop'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['success'] == true) {
          _currentState = data['data']?['state'];
          print('⏹️ 停止录音');
        }

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'state': data['data']?['state'],
          'is_recording': data['data']?['is_recording'] ?? false,
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '停止录音失败',
        };
      }
    } catch (e) {
      print('❌ 停止录音异常: $e');
      return {
        'success': false,
        'message': '停止录音失败: $e',
      };
    }
  }

  // ============== 文本消息 ==============

  /// 发送文本消息
  Future<Map<String, dynamic>> sendTextMessage(String text) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/message/send'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['success'] == true) {
          _currentState = data['data']?['state'];
          print('💬 发送文本消息: $text');
        }

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'text': data['data']?['text'],
          'state': data['data']?['state'],
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '发送文本消息失败',
        };
      }
    } catch (e) {
      print('❌ 发送文本消息异常: $e');
      return {
        'success': false,
        'message': '发送文本消息失败: $e',
      };
    }
  }

  // ============== 对话历史 ==============

  /// 获取对话历史
  Future<Map<String, dynamic>> getConversationHistory({int limit = 50}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/voice/conversation/history?limit=$limit'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'messages': data['data']?['messages'] ?? [],
          'total_count': data['data']?['total_count'] ?? 0,
        };
      } else {
        throw Exception('获取对话历史失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 获取对话历史异常: $e');
      return {
        'success': false,
        'message': '获取对话历史失败: $e',
        'messages': [],
        'total_count': 0,
      };
    }
  }

  // ============== 健康检查 ==============

  /// 检查语音系统健康状态
  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/voice/health'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        return {
          'healthy': data['healthy'] ?? false,
          'message': data['message'] ?? '',
          'components': data['components'] ?? {},
          'state': data['state'],
          'stats': data['stats'] ?? {},
        };
      } else {
        throw Exception('健康检查失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 健康检查异常: $e');
      return {
        'healthy': false,
        'message': '健康检查失败: $e',
        'components': {
          'session': false,
          'websocket': false,
          'recorder': false,
          'player': false,
        },
      };
    }
  }

  // ============== 辅助方法 ==============

  /// 检查会话是否就绪
  Future<bool> isReady() async {
    try {
      final statusResult = await getSessionStatus();
      return statusResult['success'] == true &&
             statusResult['data']?['initialized'] == true;
    } catch (e) {
      return false;
    }
  }

  /// 等待会话就绪（带超时）
  Future<bool> waitUntilReady({Duration timeout = const Duration(seconds: 10)}) async {
    final startTime = DateTime.now();

    while (DateTime.now().difference(startTime) < timeout) {
      if (await isReady()) {
        return true;
      }
      await Future.delayed(const Duration(milliseconds: 500));
    }

    return false;
  }

  /// 清理会话状态
  void clearSessionState() {
    _isSessionInitialized = false;
    _sessionId = null;
    _currentState = null;
  }
}
