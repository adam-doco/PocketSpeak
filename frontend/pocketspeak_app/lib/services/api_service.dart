import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // 基础URL - 根据后端实际地址修改
  static const String baseUrl = 'http://localhost:8000';

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

  /// 获取验证码
  Future<String> getVerifyCode() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/get-verify-code'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['verify_code'] ?? '000000';
      } else {
        throw Exception('获取验证码失败: ${response.statusCode}');
      }
    } catch (e) {
      // 模拟验证码，实际应该从后端获取
      return _generateMockVerifyCode();
    }
  }

  /// 检查绑定状态
  Future<bool> checkBindStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/check-bind-status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['is_bound'] ?? false;
      } else {
        throw Exception('检查绑定状态失败: ${response.statusCode}');
      }
    } catch (e) {
      // 模拟绑定状态 - 30秒后自动返回成功
      await Future.delayed(const Duration(seconds: 1));
      final now = DateTime.now().millisecondsSinceEpoch;
      final mockSuccess = (now % 30000) > 25000; // 30秒周期中的最后5秒返回成功
      return mockSuccess;
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