import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // 基础URL - 根据后端实际地址修改
  static const String baseUrl = 'http://localhost:8000';

  // 存储绑定过程中的challenge值
  String? _currentChallenge;
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
        Uri.parse('$baseUrl/api/device/mark-activated'),
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
}