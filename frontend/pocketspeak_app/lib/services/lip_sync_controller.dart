import 'dart:async';
import 'package:flutter/foundation.dart';
import '../widgets/live2d_widget.dart';

/// 嘴部同步控制器
///
/// 负责在语音播放时控制Live2D模型的嘴部动画
/// 当语音播放时，会循环播放嘴部动作；语音结束时，停止嘴部动作并恢复待机状态
class LipSyncController {
  final Live2DController? live2dController;

  /// 是否正在播放嘴部动画
  bool _isPlaying = false;

  /// 嘴部动画定时器
  Timer? _lipSyncTimer;

  /// 嘴部动画刷新间隔（毫秒）
  final int _intervalMs;

  /// 使用的表情名称（默认使用B1麦克风）
  final String _expressionName;

  LipSyncController(
    this.live2dController, {
    int intervalMs = 200,
    String expressionName = 'B1麦克风',
  })  : _intervalMs = intervalMs,
        _expressionName = expressionName;

  /// 是否正在播放嘴部动画
  bool get isPlaying => _isPlaying;

  /// 开始嘴部同步动画
  ///
  /// 在语音播放开始时调用此方法
  /// 会以固定间隔循环播放嘴部表情
  void startLipSync() {
    if (_isPlaying) {
      debugPrint('👄 嘴部动画已在播放中，忽略重复启动');
      return;
    }

    if (live2dController == null) {
      debugPrint('⚠️ Live2D控制器未初始化，无法启动嘴部同步');
      return;
    }

    _isPlaying = true;
    debugPrint('👄 开始嘴部同步动画 (间隔: ${_intervalMs}ms, 表情: $_expressionName)');

    // 立即播放一次
    _playLipSyncFrame();

    // 启动定时器，循环播放
    _lipSyncTimer = Timer.periodic(
      Duration(milliseconds: _intervalMs),
      (_) => _playLipSyncFrame(),
    );
  }

  /// 播放一帧嘴部动画
  void _playLipSyncFrame() {
    if (!_isPlaying || live2dController == null) {
      return;
    }

    try {
      live2dController!.playExpression(_expressionName);
    } catch (e) {
      debugPrint('❌ 播放嘴部动画失败: $e');
    }
  }

  /// 停止嘴部同步动画
  ///
  /// 在语音播放结束时调用此方法
  /// 会停止嘴部动画并恢复待机状态
  Future<void> stopLipSync() async {
    if (!_isPlaying) {
      debugPrint('👄 嘴部动画未在播放，忽略停止请求');
      return;
    }

    debugPrint('👄 停止嘴部同步动画');

    _isPlaying = false;

    // 取消定时器
    _lipSyncTimer?.cancel();
    _lipSyncTimer = null;

    // 恢复待机状态
    if (live2dController != null) {
      try {
        await live2dController!.playMotion('', 0);
        debugPrint('👄 已恢复待机状态');
      } catch (e) {
        debugPrint('❌ 恢复待机状态失败: $e');
      }
    }
  }

  /// 暂停嘴部动画（不恢复待机状态）
  ///
  /// 用于临时暂停嘴部动画，但不改变模型状态
  void pauseLipSync() {
    if (!_isPlaying) return;

    debugPrint('👄 暂停嘴部同步动画');
    _isPlaying = false;
    _lipSyncTimer?.cancel();
    _lipSyncTimer = null;
  }

  /// 恢复嘴部动画
  ///
  /// 从暂停状态恢复播放
  void resumeLipSync() {
    if (_isPlaying) return;

    debugPrint('👄 恢复嘴部同步动画');
    startLipSync();
  }

  /// 清理资源
  void dispose() {
    if (_isPlaying) {
      debugPrint('👄 LipSyncController dispose: 停止嘴部动画');
      _lipSyncTimer?.cancel();
      _lipSyncTimer = null;
      _isPlaying = false;
    }
  }
}
