import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // 基础URL - 根据后端实际地址修改
  static const String baseUrl = 'http://localhost:8000';

  // 存储绑定过程中的challenge值
  String? _currentChallenge;
  // ignore: unused_field
  bool _isBindingStarted = false;

  /// 获取设备ID
  Future<String> getDeviceId() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/device-id'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['device_id'] ?? 'UNKNOWN_DEVICE';
      } else {
        throw Exception('获取设备ID失败: ${response.statusCode}');
      }
    } catch (e) {
      // 模拟设备ID，实际应该通过py-xiaozhi获取
      return 'DEV_${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}';
    }
  }

  /// 启动设备激活流程，获取验证码 - 使用PocketSpeak真实激活逻辑
  Future<Map<String, dynamic>> startDeviceBinding({int timeout = 300}) async {
    try {
      // 使用新的PocketSpeak激活API
      final response = await http.get(
        Uri.parse('$baseUrl/api/device/code'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          _currentChallenge = data['server_response']?['activation']?['challenge'] ?? 'mock_challenge';
          _isBindingStarted = true;
          return {
            'success': true,
            'verification_code': data['verification_code'] ?? '000000',
            'challenge': _currentChallenge,
            'websocket_url': null,
            'access_token': null,
            'message': data['message'] ?? 'PocketSpeak激活流程已启动',
            'device_id': data['device_id'] ?? '',
            'server_response': data['server_response']
          };
        } else {
          // 如果设备已激活，返回特殊状态
          if (data['message']?.contains('已激活') == true) {
            return {
              'success': true,
              'verification_code': null,
              'challenge': null,
              'websocket_url': null,
              'access_token': null,
              'message': '设备已激活，无需重复激活',
              'already_activated': true
            };
          }
          throw Exception(data['message'] ?? '启动激活失败');
        }
      } else {
        throw Exception('启动激活失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      // 模拟激活响应数据
      _currentChallenge = 'mock_challenge_${DateTime.now().millisecondsSinceEpoch}';
      _isBindingStarted = true;
      return {
        'success': true,
        'verification_code': _generateMockVerifyCode(),
        'challenge': _currentChallenge,
        'websocket_url': null,
        'access_token': null,
        'message': '模拟激活流程已启动（后端未连接）'
      };
    }
  }

  /// 获取验证码（兼容旧接口）
  Future<String> getVerifyCode() async {
    final result = await startDeviceBinding();
    return result['verification_code'] ?? '000000';
  }

  /// 检查绑定状态（不需要轮询的基础状态查询）
  Future<Map<String, dynamic>> getDeviceBindStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/device-bind-status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'device_id': data['device_id'],
          'is_activated': data['is_activated'] ?? false,
          'device_source': data['device_source'] ?? 'unknown',
          'message': data['message'] ?? ''
        };
      } else {
        throw Exception('查询绑定状态失败: ${response.statusCode}');
      }
    } catch (e) {
      return {
        'device_id': 'mock_device',
        'is_activated': false,
        'device_source': 'mock',
        'message': '模拟状态（后端未连接）'
      };
    }
  }

  /// 等待激活确认（检查PocketSpeak激活状态）
  Future<Map<String, dynamic>> waitForBindConfirmation({int timeout = 300}) async {
    try {
      // 使用PocketSpeak激活状态检查API
      final response = await http.get(
        Uri.parse('$baseUrl/api/device/activation-status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final isActivated = data['is_activated'] ?? false;

        return {
          'success': isActivated,
          'is_activated': isActivated,
          'websocket_url': isActivated ? 'wss://api.xiaozhi.com/v1/ws' : null,
          'access_token': isActivated ? 'pocketspeak_activated' : null,
          'message': data['message'] ?? (isActivated ? '设备激活成功' : '等待用户在xiaozhi.me完成绑定...'),
          'device_id': data['device_id'] ?? '',
          'serial_number': data['serial_number'] ?? '',
          'activation_status': data['activation_status'] ?? ''
        };
      } else {
        throw Exception('激活状态查询失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      // 模拟轮询结果
      await Future.delayed(const Duration(milliseconds: 500));
      final now = DateTime.now().millisecondsSinceEpoch;
      final mockSuccess = (now % 30000) > 25000; // 30秒周期中的最后5秒返回成功

      return {
        'success': mockSuccess,
        'is_activated': mockSuccess,
        'websocket_url': mockSuccess ? 'wss://api.xiaozhi.com/v1/ws' : null,
        'access_token': mockSuccess ? 'mock_token_$now' : null,
        'message': mockSuccess ? '激活成功（模拟）' : '等待用户在xiaozhi.me完成绑定...',
        'error_detail': null
      };
    }
  }

  /// 检查绑定状态（兼容旧接口）
  Future<bool> checkBindStatus() async {
    final result = await waitForBindConfirmation();
    return result['success'] ?? false;
  }

  /// 手动标记设备为已激活（用户在xiaozhi.me完成绑定后调用）
  Future<Map<String, dynamic>> markDeviceActivated() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/device/mark-activated-v2'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'is_activated': data['is_activated'] ?? false
        };
      } else {
        throw Exception('标记激活失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      return {
        'success': false,
        'message': '标记激活失败: $e',
        'is_activated': false
      };
    }
  }

  /// 生成模拟验证码
  String _generateMockVerifyCode() {
    final random = DateTime.now().millisecondsSinceEpoch % 900000 + 100000;
    return random.toString();
  }

  /// 发送音频数据（为聊天页面预留）
  Future<Map<String, dynamic>> sendAudio(List<int> audioData) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/send-audio'),
      );

      request.files.add(
        http.MultipartFile.fromBytes(
          'audio',
          audioData,
          filename: 'audio.opus',
        ),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('发送音频失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  /// 发送文本消息（为聊天页面预留）
  Future<Map<String, dynamic>> sendText(String text) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/send-text'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'text': text}),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('发送文本失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  // ============== WebSocket连接管理接口 ==============

  /// 启动WebSocket连接
  Future<Map<String, dynamic>> startWebSocketConnection() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/ws/start'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'data': data['data'] ?? {},
        };
      } else {
        final errorData = json.decode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '启动WebSocket连接失败',
          'data': errorData['detail']?['data'] ?? {},
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'WebSocket连接启动失败: $e',
        'data': {},
      };
    }
  }

  /// 停止WebSocket连接
  Future<Map<String, dynamic>> stopWebSocketConnection() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/ws/stop'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'data': data['data'] ?? {},
        };
      } else {
        final errorData = json.decode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? '停止WebSocket连接失败',
          'data': errorData['detail']?['data'] ?? {},
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'WebSocket连接停止失败: $e',
        'data': {},
      };
    }
  }

  /// 获取WebSocket连接状态
  Future<Map<String, dynamic>> getWebSocketStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/ws/status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'data': data['data'] ?? {},
        };
      } else {
        throw Exception('获取WebSocket状态失败: ${response.statusCode}');
      }
    } catch (e) {
      return {
        'success': false,
        'data': {
          'state': 'error',
          'connected': false,
          'authenticated': false,
          'error': 'WebSocket状态查询失败: $e',
        },
      };
    }
  }

  /// 重新连接WebSocket
  Future<Map<String, dynamic>> reconnectWebSocket() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/ws/reconnect'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'data': data['data'] ?? {},
        };
      } else {
        final errorData = json.decode(response.body);
        return {
          'success': false,
          'message': errorData['detail']?['message'] ?? 'WebSocket重连失败',
          'data': errorData['detail']?['data'] ?? {},
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'WebSocket重连失败: $e',
        'data': {},
      };
    }
  }

  /// 获取WebSocket健康状态
  Future<Map<String, dynamic>> getWebSocketHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/ws/health'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('获取WebSocket健康状态失败: ${response.statusCode}');
      }
    } catch (e) {
      return {
        'healthy': false,
        'connection_state': 'error',
        'connected': false,
        'authenticated': false,
        'message': 'WebSocket健康检查失败: $e',
      };
    }
  }

  /// 获取WebSocket统计信息
  Future<Map<String, dynamic>> getWebSocketStats() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/ws/stats'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'data': data['data'] ?? {},
        };
      } else {
        throw Exception('获取WebSocket统计信息失败: ${response.statusCode}');
      }
    } catch (e) {
      return {
        'success': false,
        'data': {},
        'error': 'WebSocket统计信息获取失败: $e',
      };
    }
  }

  /// 检查设备是否可以建立WebSocket连接（综合检查）
  Future<Map<String, dynamic>> checkWebSocketReadiness() async {
    try {
      // 1. 检查设备激活状态
      final activationStatus = await waitForBindConfirmation();
      if (!activationStatus['is_activated']) {
        return {
          'ready': false,
          'reason': 'device_not_activated',
          'message': '设备未激活，请先完成设备激活流程',
          'activation_status': activationStatus,
        };
      }

      // 2. 检查WebSocket健康状态
      final healthStatus = await getWebSocketHealth();

      return {
        'ready': activationStatus['is_activated'] && healthStatus['healthy'],
        'reason': activationStatus['is_activated'] ? 'ready' : 'device_not_activated',
        'message': activationStatus['is_activated'] ? 'WebSocket连接就绪' : '设备未激活',
        'activation_status': activationStatus,
        'websocket_health': healthStatus,
      };
    } catch (e) {
      return {
        'ready': false,
        'reason': 'check_failed',
        'message': 'WebSocket就绪状态检查失败: $e',
      };
    }
  }

  // ============== V1.2: 用户档案管理接口 ==============

  /// 创建用户档案
  Future<Map<String, dynamic>> createUserProfile({
    required String userId,
    required String deviceId,
    required String learningGoal,
    required String englishLevel,
    required String ageGroup,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/user/init'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'device_id': deviceId,
          'learning_goal': learningGoal,
          'english_level': englishLevel,
          'age_group': ageGroup,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'user_profile': data['user_profile'],
        };
      } else if (response.statusCode == 400) {
        final data = json.decode(response.body);
        return {
          'success': false,
          'message': data['detail'] ?? '创建用户档案失败',
          'user_profile': null,
        };
      } else {
        throw Exception('创建用户档案失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      // ignore: avoid_print
      print('❌ 创建用户档案异常: $e');
      return {
        'success': false,
        'message': '网络错误，无法同步用户档案到后端',
        'user_profile': null,
      };
    }
  }

  /// 获取用户档案
  Future<Map<String, dynamic>> getUserProfile(String userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/user/$userId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'user_profile': data['user_profile'],
        };
      } else if (response.statusCode == 404) {
        return {
          'success': false,
          'message': '用户不存在',
          'user_profile': null,
        };
      } else {
        throw Exception('获取用户档案失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      // ignore: avoid_print
      print('❌ 获取用户档案异常: $e');
      return {
        'success': false,
        'message': '网络错误，无法获取用户档案',
        'user_profile': null,
      };
    }
  }

  /// 更新用户档案
  Future<Map<String, dynamic>> updateUserProfile({
    required String userId,
    String? learningGoal,
    String? englishLevel,
    String? ageGroup,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (learningGoal != null) body['learning_goal'] = learningGoal;
      if (englishLevel != null) body['english_level'] = englishLevel;
      if (ageGroup != null) body['age_group'] = ageGroup;

      final response = await http.put(
        Uri.parse('$baseUrl/api/user/$userId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'success': data['success'] ?? false,
          'message': data['message'] ?? '',
          'user_profile': data['user_profile'],
        };
      } else if (response.statusCode == 404) {
        return {
          'success': false,
          'message': '用户不存在',
          'user_profile': null,
        };
      } else {
        throw Exception('更新用户档案失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      // ignore: avoid_print
      print('❌ 更新用户档案异常: $e');
      return {
        'success': false,
        'message': '网络错误，无法更新用户档案',
        'user_profile': null,
      };
    }
  }
}