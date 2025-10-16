import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

/// 语音交互服务
/// 封装与后端语音API的所有交互
class VoiceService {
  static const String baseUrl = 'http://localhost:8000';
  static const String wsUrl = 'ws://localhost:8000/api/voice/ws';

  // 会话状态
  bool _isSessionInitialized = false;
  String? _sessionId;
  String? _currentState;

  // 🚀 WebSocket 连接（实时音频推送）
  WebSocketChannel? _wsChannel;
  StreamSubscription? _wsSubscription;
  bool _isWsConnected = false;

  // 🔥 自动重连控制（参照py-xiaozhi）
  bool _autoReconnect = false;  // 自动重连开关
  int _reconnectAttempts = 0;   // 重连尝试次数
  final int _maxReconnectAttempts = 5;  // 最大重连次数
  Timer? _reconnectTimer;       // 重连定时器

  // 🚀 音频帧回调（模仿py-xiaozhi的即时播放）
  void Function(String audioData)? onAudioFrameReceived;
  void Function(String text)? onUserTextReceived;  // 用户语音识别文字
  void Function(String text)? onTextReceived;  // AI文本
  void Function(String emoji)? onEmotionReceived;  // AI表情emoji
  void Function(String state)? onStateChanged;

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

          // ✅ 精简：移除初始化成功日志
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

        // ✅ 精简：移除关闭会话日志
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
          // ✅ 精简：移除开始录音日志
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
          // ✅ 精简：移除停止录音日志
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
          // ✅ 精简：移除发送消息日志
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

  /// 获取已完成的句子（用于逐句播放）
  Future<Map<String, dynamic>> getCompletedSentences({int lastSentenceIndex = 0}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/voice/conversation/sentences?last_sentence_index=$lastSentenceIndex'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'data': data['data'] ?? {},
        };
      } else {
        throw Exception('获取句子失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 获取句子异常: $e');
      return {
        'success': false,
        'message': '获取句子失败: $e',
        'data': {
          'has_new_sentences': false,
          'is_complete': false,
        },
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

  // ============== WebSocket 实时音频推送 ==============

  /// 🚀 连接WebSocket（模仿py-xiaozhi的即时播放架构）
  Future<bool> connectWebSocket({bool enableAutoReconnect = true}) async {
    // 🔥 先取消重连定时器
    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    // 🔥 先断开旧连接，防止hot reload导致重复连接
    if (_isWsConnected) {
      await disconnectWebSocket();
    }

    try {
      print('🔌 正在连接WebSocket: $wsUrl');

      _wsChannel = WebSocketChannel.connect(Uri.parse(wsUrl));

      // 监听WebSocket消息
      _wsSubscription = _wsChannel!.stream.listen(
        (message) {
          _handleWebSocketMessage(message);
        },
        onError: (error) {
          print('❌ WebSocket错误: $error');
          _isWsConnected = false;
          // 🔥 触发自动重连
          if (_autoReconnect) {
            _scheduleReconnect();
          }
        },
        onDone: () {
          print('🔌 WebSocket连接已关闭');
          _isWsConnected = false;
          // 🔥 触发自动重连
          if (_autoReconnect) {
            _scheduleReconnect();
          }
        },
      );

      _isWsConnected = true;
      _autoReconnect = enableAutoReconnect;  // 🔥 设置自动重连开关
      _reconnectAttempts = 0;  // 🔥 重置重连次数
      print('✅ WebSocket连接成功');
      return true;
    } catch (e) {
      print('❌ WebSocket连接失败: $e');
      _isWsConnected = false;
      // 🔥 触发自动重连
      if (enableAutoReconnect) {
        _autoReconnect = true;
        _scheduleReconnect();
      }
      return false;
    }
  }

  /// 🔥 调度自动重连（指数退避算法）
  void _scheduleReconnect() {
    // 检查重连次数
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      print('❌ 已达到最大重连次数($_maxReconnectAttempts)，停止重连');
      _autoReconnect = false;
      return;
    }

    // 取消旧定时器
    _reconnectTimer?.cancel();

    // 计算延迟时间（指数退避：1s, 2s, 4s, 8s, 16s）
    final delay = Duration(seconds: (1 << _reconnectAttempts).clamp(1, 16));
    _reconnectAttempts++;

    print('🔄 将在 ${delay.inSeconds} 秒后尝试第 $_reconnectAttempts 次重连');

    // 设置定时器
    _reconnectTimer = Timer(delay, () async {
      print('🔄 正在尝试第 $_reconnectAttempts 次重连...');
      final success = await connectWebSocket(enableAutoReconnect: true);
      if (success) {
        print('✅ 重连成功！');
        _reconnectAttempts = 0;  // 重置重连次数
      }
    });
  }

  /// 处理WebSocket消息
  void _handleWebSocketMessage(dynamic message) {
    try {
      final data = jsonDecode(message);
      final type = data['type'];

      // ✅ 精简：移除所有消息的debug日志（太多了）

      switch (type) {
        case 'audio_frame':
          // 🚀 收到音频帧，立即回调（模仿py-xiaozhi的write_audio）
          if (onAudioFrameReceived != null) {
            onAudioFrameReceived!(data['data']);
          }
          break;

        case 'user_text':
          // 🚀 收到用户语音识别文字
          if (onUserTextReceived != null && data['data'] != null) {
            onUserTextReceived!(data['data']);
          }
          break;

        case 'text':
          // 🚀 收到AI文本消息（新格式）
          if (onTextReceived != null && data['data'] != null) {
            onTextReceived!(data['data']);
          }
          break;

        case 'llm':
          // 🎭 收到LLM消息（包含emoji表情）
          // 示例: {"type":"llm", "text": "😊", "emotion": "smile"}
          if (data['text'] != null) {
            // 如果text就是emoji，触发emotion回调
            if (onEmotionReceived != null) {
              onEmotionReceived!(data['text']);
            }
          }
          // 如果有独立的emotion字段也可以使用
          if (data['emotion'] != null && onEmotionReceived != null) {
            // emotion字段可能是英文描述，但我们主要使用text中的emoji
            // ✅ 精简：移除emotion日志（已在chat_page中打印）
          }
          break;

        case 'ai_response':
          // 兼容旧格式
          if (onTextReceived != null && data['data']?['text'] != null) {
            onTextReceived!(data['data']['text']);
          }
          break;

        case 'state_change':
          // 状态变化
          if (onStateChanged != null && data['data']?['state'] != null) {
            onStateChanged!(data['data']['state']);
          }
          break;

        case 'error':
          print('❌ 服务器错误: ${data['message']}');
          break;

        default:
          print('⚠️ 未知消息类型: $type');
      }
    } catch (e) {
      print('❌ 处理WebSocket消息失败: $e');
    }
  }

  /// 断开WebSocket连接
  Future<void> disconnectWebSocket() async {
    if (!_isWsConnected && _wsChannel == null) {
      return;
    }

    try {
      // 🔥 主动断开时禁用自动重连
      _autoReconnect = false;
      _reconnectTimer?.cancel();
      _reconnectTimer = null;

      // 清空回调，防止重复触发
      onAudioFrameReceived = null;
      onUserTextReceived = null;
      onTextReceived = null;
      onEmotionReceived = null;
      onStateChanged = null;

      await _wsSubscription?.cancel();
      await _wsChannel?.sink.close();
      _wsChannel = null;
      _wsSubscription = null;
      _isWsConnected = false;
      print('✅ WebSocket已主动断开');
    } catch (e) {
      print('❌ 断开WebSocket失败: $e');
    }
  }

  /// 获取WebSocket连接状态
  bool get isWebSocketConnected => _isWsConnected;
}
