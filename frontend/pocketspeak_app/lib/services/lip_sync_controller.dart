import 'dart:async';
import 'package:flutter/foundation.dart';
import '../widgets/live2d_widget.dart';

/// 🔥 嘴部同步控制器（直接调用HTML中的嘴部参数控制）
///
/// 负责在语音播放时控制Live2D模型的嘴部动画
/// 使用HTML中新增的 window.startLipSync() 和 window.stopLipSync() 方法
/// 这些方法直接操作Live2D模型的嘴部参数，实现更自然的嘴部动作
class LipSyncController {
  final Live2DController? live2dController;

  /// 是否正在播放嘴部动画
  bool _isPlaying = false;

  /// 音频活动检测定时器
  Timer? _inactivityTimer;

  /// 音频不活跃超时时间（毫秒）
  static const int _inactivityTimeout = 2000;

  LipSyncController(this.live2dController);

  /// 是否正在播放嘴部动画
  bool get isPlaying => _isPlaying;

  /// 开始嘴部同步动画
  ///
  /// 在语音播放开始时调用此方法
  /// 会启动HTML中的嘴部参数循环动画
  void startLipSync() {
    if (_isPlaying) {
      // 已经在播放，重置不活跃定时器
      _resetInactivityTimer();
      return;
    }

    if (live2dController == null) {
      debugPrint('⚠️ Live2D控制器未初始化，无法启动嘴部同步');
      return;
    }

    _isPlaying = true;
    debugPrint('👄 开始嘴部同步动画（调用 Live2DController.startLipSync）');

    try {
      // 🔥 调用Live2DController的嘴部动画控制方法
      live2dController!.startLipSync();

      // 启动不活跃检测定时器
      _startInactivityTimer();
    } catch (e) {
      debugPrint('❌ 启动嘴部动画失败: $e');
      _isPlaying = false;
    }
  }

  /// 刷新音频活动（收到新音频帧时调用）
  ///
  /// 重置不活跃定时器，确保在持续接收音频时嘴部动画不会停止
  void refreshActivity() {
    if (_isPlaying) {
      _resetInactivityTimer();
    }
  }

  /// 启动不活跃检测定时器
  ///
  /// 如果超过指定时间没有新音频帧，自动停止嘴部动画
  void _startInactivityTimer() {
    _inactivityTimer?.cancel();
    _inactivityTimer = Timer(Duration(milliseconds: _inactivityTimeout), () {
      if (_isPlaying) {
        debugPrint('👄 音频流不活跃超时，自动停止嘴部动画');
        stopLipSync();
      }
    });
  }

  /// 重置不活跃定时器
  void _resetInactivityTimer() {
    _inactivityTimer?.cancel();
    _startInactivityTimer();
  }

  /// 停止嘴部同步动画
  ///
  /// 在语音播放结束时调用此方法
  /// 会停止HTML中的嘴部动画并重置嘴部参数为闭合状态
  Future<void> stopLipSync() async {
    if (!_isPlaying) {
      debugPrint('👄 嘴部动画未在播放，忽略停止请求');
      return;
    }

    debugPrint('👄 停止嘴部同步动画（调用 Live2DController.stopLipSync）');

    // 取消不活跃定时器
    _inactivityTimer?.cancel();
    _inactivityTimer = null;

    _isPlaying = false;

    if (live2dController != null) {
      try {
        // 🔥 调用Live2DController的嘴部动画停止方法
        await live2dController!.stopLipSync();
        debugPrint('👄 嘴部动画已停止，嘴部参数已重置');
      } catch (e) {
        debugPrint('❌ 停止嘴部动画失败: $e');
      }
    }
  }

  /// 暂停嘴部动画（等同于停止）
  ///
  /// 用于临时暂停嘴部动画
  void pauseLipSync() {
    if (!_isPlaying) return;

    debugPrint('👄 暂停嘴部同步动画');
    stopLipSync();
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
    // 取消定时器
    _inactivityTimer?.cancel();
    _inactivityTimer = null;

    if (_isPlaying) {
      debugPrint('👄 LipSyncController dispose: 停止嘴部动画');
      _isPlaying = false;

      // 同步调用停止方法
      if (live2dController != null) {
        try {
          live2dController!.stopLipSync();
        } catch (e) {
          debugPrint('❌ dispose时停止嘴部动画失败: $e');
        }
      }
    }
  }
}
