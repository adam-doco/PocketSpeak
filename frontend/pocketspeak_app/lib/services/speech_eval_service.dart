// 语音评分服务 - PocketSpeak V1.6
// 调用后端API进行语音评分分析

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/speech_feedback.dart';

class SpeechEvalService {
  // 基础URL - 与其他服务保持一致
  static const String baseUrl = 'http://localhost:8000';

  /// 评估语音文本
  ///
  /// Args:
  ///   transcript: 语音识别的文本
  ///
  /// Returns:
  ///   SpeechFeedbackResponse: 评分结果
  Future<SpeechFeedbackResponse> evaluateSpeech(String transcript) async {
    try {
      print('🎯 评估语音: $transcript');

      final response = await http.post(
        Uri.parse('$baseUrl/api/eval/speech-feedback'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'transcript': transcript,
        }),
      );

      print('📡 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('✅ 评分成功: 综合得分 ${data['overall_score']}');
        return SpeechFeedbackResponse.fromJson(data);
      } else if (response.statusCode == 400) {
        // 业务错误（如transcript为空）
        final error = json.decode(response.body);
        print('❌ 评分失败: ${error['detail']}');
        throw Exception(error['detail'] ?? '评分失败');
      } else if (response.statusCode == 503) {
        // 服务不可用
        final error = json.decode(response.body);
        print('❌ 服务不可用: ${error['detail']}');
        throw Exception(error['detail'] ?? '语音评分服务未启用');
      } else {
        throw Exception('评分失败: HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 评估语音异常: $e');
      rethrow;
    }
  }

  /// 检查服务健康状态
  ///
  /// Returns:
  ///   bool: 服务是否可用
  Future<bool> checkHealth() async {
    try {
      print('🏥 检查语音评分服务状态');

      final response = await http.get(
        Uri.parse('$baseUrl/api/eval/health'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final status = data['status'];
        print('✅ 服务状态: $status');
        return status == 'healthy';
      } else {
        print('❌ 服务不可用: HTTP ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('❌ 检查服务状态异常: $e');
      return false;
    }
  }
}
