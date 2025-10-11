import 'dart:convert';
import 'dart:typed_data';
import 'dart:io';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

/// PocketSpeak 音频播放服务
///
/// 功能:
/// 1. 播放Base64编码的OPUS音频数据
/// 2. 管理播放状态
/// 3. 提供播放控制接口
///
/// 使用just_audio以支持iOS上的OPUS格式
class AudioPlayerService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlaying = false;
  String? _currentAudioId;

  /// 获取播放状态
  bool get isPlaying => _isPlaying;

  /// 获取当前播放的音频ID
  String? get currentAudioId => _currentAudioId;

  /// 获取播放状态流(用于监听播放完成事件)
  Stream<PlayerState> get playerStateStream => _audioPlayer.playerStateStream;

  AudioPlayerService() {
    // 监听播放状态变化
    _audioPlayer.playerStateStream.listen((state) {
      if (state.playing) {
        _isPlaying = true;
        print('🔊 音频正在播放');
      } else {
        _isPlaying = false;
        if (state.processingState == ProcessingState.completed) {
          _currentAudioId = null;
          print('🔊 音频播放完成');
        }
      }
    });
  }

  /// 播放Base64编码的音频数据
  ///
  /// [audioData] Base64编码的音频数据字符串
  /// [audioId] 音频唯一标识(可选,用于追踪当前播放的音频)
  ///
  /// 返回播放是否成功
  Future<bool> playBase64Audio(String audioData, {String? audioId}) async {
    try {
      print('🔊 准备播放音频 (ID: $audioId)');

      // 如果正在播放,先停止
      if (_isPlaying) {
        print('⏹️ 停止当前播放');
        await stop();
      }

      // Base64解码为字节数组
      Uint8List audioBytes = base64.decode(audioData);
      print('✅ Base64解码成功: ${audioBytes.length} bytes');

      // 获取临时目录
      final tempDir = await getTemporaryDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final tempFile = File('${tempDir.path}/audio_$timestamp.wav');

      // 写入临时文件
      await tempFile.writeAsBytes(audioBytes);
      print('✅ 音频文件已写入: ${tempFile.path}');

      // 使用just_audio播放OPUS音频
      await _audioPlayer.setFilePath(tempFile.path);
      await _audioPlayer.play();

      _currentAudioId = audioId;
      _isPlaying = true;

      print('✅ 音频开始播放');
      return true;
    } catch (e) {
      print('❌ 播放音频失败: $e');
      _isPlaying = false;
      _currentAudioId = null;
      return false;
    }
  }

  /// 暂停播放
  Future<void> pause() async {
    try {
      await _audioPlayer.pause();
      print('⏸️ 音频已暂停');
    } catch (e) {
      print('❌ 暂停音频失败: $e');
    }
  }

  /// 恢复播放
  Future<void> resume() async {
    try {
      await _audioPlayer.play();
      print('▶️ 音频已恢复');
    } catch (e) {
      print('❌ 恢复播放失败: $e');
    }
  }

  /// 停止播放
  Future<void> stop() async {
    try {
      await _audioPlayer.stop();
      _isPlaying = false;
      _currentAudioId = null;
      print('⏹️ 音频已停止');
    } catch (e) {
      print('❌ 停止播放失败: $e');
    }
  }

  /// 释放资源
  void dispose() {
    _audioPlayer.dispose();
    print('🔇 音频播放器已释放');
  }
}
