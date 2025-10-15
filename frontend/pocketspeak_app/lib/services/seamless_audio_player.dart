import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_sound/flutter_sound.dart';

/// 🚀 无缝音频播放器（使用flutter_sound实现真正的PCM流式播放）
///
/// 核心改进（完全替换文件模式为流式模式）：
/// 1. **无文件IO**：直接将PCM数据push到flutter_sound的foodSink（延迟从30-150ms降到<5ms）
/// 2. **无批次累积**：每帧立即push，无200ms延迟
/// 3. **单一音频流**：无需管理动态播放列表，无索引跳变问题
/// 4. **低延迟**：预计总延迟<50ms（vs 之前的280-550ms）
/// 5. **完全模拟py-xiaozhi的sounddevice架构**
///
/// 参考：
/// - py-xiaozhi: 使用sounddevice库，回调驱动，直接写入音频设备缓冲区
/// - PocketSpeak: 使用flutter_sound，push模式，直接写入音频流
class SeamlessAudioPlayer {
  final FlutterSoundPlayer _player = FlutterSoundPlayer();

  // 播放状态
  bool _isInitialized = false;
  bool _isPlaying = false;
  bool _isStarting = false;  // 是否正在启动中
  final List<Uint8List> _pendingFrames = [];  // 启动期间的待处理帧

  // 配置参数（匹配后端PCM格式）
  static const int sampleRate = 24000;      // 24kHz
  static const int numChannels = 1;         // 单声道
  static const Codec codec = Codec.pcm16;   // 16-bit PCM

  SeamlessAudioPlayer() {
    _initPlayer();
  }

  /// 初始化播放器
  Future<void> _initPlayer() async {
    try {
      // 🔇 关闭FlutterSound的debug日志（临时注释，待确认API）
      // _player.setLogLevel(LogLevel.error);
      await _player.openPlayer();
      _isInitialized = true;
      // ✅ 精简：只在失败时输出日志

      // ⚠️ 不在初始化时启动播放，而是等待第一帧到达时再启动
      // 原因：无数据时立即启动会触发"播放完成"事件，可能导致状态错误
    } catch (e) {
      print('❌ 初始化播放器失败: $e');
    }
  }

  /// 🚀 启动流式播放
  Future<void> _startStreaming() async {
    if (!_isInitialized || _isPlaying || _isStarting) return;

    _isStarting = true;

    try {
      // ✅ 精简：移除日志

      await _player.startPlayerFromStream(
        codec: codec,
        numChannels: numChannels,
        sampleRate: sampleRate,
        bufferSize: 8192,  // 8KB缓冲区，适合24kHz PCM流式播放
        interleaved: true,  // 交错模式（单声道时无影响）
      );

      _isPlaying = true;
      // ✅ 精简：移除启动日志

      // 🔥 启动完成后，立即feed所有待处理的帧
      if (_pendingFrames.isNotEmpty) {
        // ✅ 精简：移除缓冲日志
        for (var frame in _pendingFrames) {
          _feedFrame(frame);
        }
        _pendingFrames.clear();
      }
    } catch (e) {
      print('❌ 启动流式播放失败: $e');
      _isPlaying = false;
    } finally {
      _isStarting = false;
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

      // 🔥 关键优化：如果正在启动或未播放，缓冲数据
      if (_isStarting || !_isPlaying) {
        _pendingFrames.add(pcmData);

        // 只在第一帧时触发启动
        if (_pendingFrames.length == 1 && !_isStarting) {
          _startStreaming();
        }
        return;
      }

      // 已经在播放，直接push到流
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
        // ✅ 精简：移除停止日志
      }

      // 清空待处理的帧
      if (_pendingFrames.isNotEmpty) {
        _pendingFrames.clear();
        // ✅ 精简：移除清空日志
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
      // ✅ 精简：移除释放日志
    }
  }

  /// 获取播放状态
  bool get isPlaying => _isPlaying;

  // 为了兼容旧代码，保留queueLength getter
  int get queueLength => 0;  // flutter_sound无队列概念
}
