import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:logger/logger.dart' show Level;

/// 🚀 流式音频播放器（使用flutter_sound实现真正的PCM流式播放）
///
/// 核心改进：
/// 1. **无文件IO**：直接将PCM数据push到flutter_sound的foodSink
/// 2. **无批次累积**：每帧立即push，无200ms延迟
/// 3. **单一音频流**：无需管理动态播放列表
/// 4. **低延迟**：预计总延迟<50ms
/// 5. **完全模拟py-xiaozhi的sounddevice架构**
///
/// 参考：
/// - py-xiaozhi: 使用sounddevice库，回调驱动，直接写入音频设备缓冲区
/// - PocketSpeak: 使用flutter_sound，push模式，直接写入音频流
class StreamingAudioPlayer {
  final FlutterSoundPlayer _player = FlutterSoundPlayer();

  // 播放状态
  bool _isInitialized = false;
  bool _isPlaying = false;

  // 配置参数（匹配后端PCM格式）
  static const int sampleRate = 24000;      // 24kHz
  static const int numChannels = 1;         // 单声道
  static const Codec codec = Codec.pcm16;   // 16-bit PCM

  StreamingAudioPlayer() {
    _initPlayer();
  }

  /// 初始化播放器
  Future<void> _initPlayer() async {
    try {
      // 🔇 关闭FlutterSound的debug日志
      _player.setLogLevel(Level.off);  // Level.off = 完全关闭日志
      await _player.openPlayer();
      _isInitialized = true;
      print('✅ Flutter Sound 播放器已初始化');
    } catch (e) {
      print('❌ 初始化 Flutter Sound 失败: $e');
    }
  }

  /// 🚀 启动流式播放
  Future<void> _startStreaming() async {
    if (!_isInitialized || _isPlaying) return;

    try {
      print('🎵 启动 PCM 流式播放 (24kHz, 单声道, PCM16)');

      await _player.startPlayerFromStream(
        codec: codec,
        numChannels: numChannels,
        sampleRate: sampleRate,
      );

      _isPlaying = true;
      print('✅ PCM 流式播放已启动');
    } catch (e) {
      print('❌ 启动流式播放失败: $e');
      _isPlaying = false;
    }
  }

  /// 🚀 添加音频帧（核心方法）
  ///
  /// 完全模拟 py-xiaozhi 的 sounddevice 模式：
  /// - py-xiaozhi: 从队列取数据 → 写入音频设备缓冲区
  /// - PocketSpeak: 从WebSocket接收 → 直接push到flutter_sound流
  void addAudioFrame(String base64Data) {
    if (!_isInitialized) {
      print('⚠️ 播放器未初始化，跳过音频帧');
      return;
    }

    try {
      // 解码Base64为PCM数据
      final pcmData = base64Decode(base64Data);

      // 如果还未开始播放，立即启动
      if (!_isPlaying) {
        _startStreaming().then((_) {
          if (_isPlaying) {
            _feedFrame(pcmData);
          }
        });
        return;
      }

      // 直接push到流
      _feedFrame(pcmData);
    } catch (e) {
      print('❌ 添加音频帧失败: $e');
    }
  }

  /// 将PCM数据feed到flutter_sound流
  void _feedFrame(Uint8List pcmData) {
    try {
      if (_player.foodSink == null) {
        print('⚠️ foodSink为空，无法feed数据');
        return;
      }

      // 🔥 关键：直接push PCM数据到流，无文件IO！
      final food = FoodData(pcmData);
      _player.foodSink!.add(food);

      // 只在首帧打印日志，避免噪音
      // print('🔊 已push音频帧: ${pcmData.length} 字节');
    } catch (e) {
      print('❌ Feed音频帧失败: $e');
    }
  }

  /// 停止播放（在新对话开始时调用）
  /// 模拟 py-xiaozhi 的 clear_audio_queue()
  Future<void> stop() async {
    if (!_isInitialized) return;

    try {
      if (_isPlaying) {
        // 停止流式播放
        await _player.stopPlayer();
        _isPlaying = false;
        print('⏹️ PCM 流式播放已停止');
      }
    } catch (e) {
      print('❌ 停止播放失败: $e');
    }
  }

  /// 释放资源
  Future<void> dispose() async {
    await stop();

    if (_isInitialized) {
      await _player.closePlayer();
      _isInitialized = false;
      print('🗑️ Flutter Sound 播放器已释放');
    }
  }

  /// 获取播放状态
  bool get isPlaying => _isPlaying;
}
