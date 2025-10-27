// 语音输入条组件 - PocketSpeak V1.7
// 优化的大按钮设计 + 录音状态反馈

import 'dart:async';
import 'package:flutter/material.dart';

class VoiceInputBar extends StatefulWidget {
  final bool isRecording;
  final bool isEnabled;
  final VoidCallback onStartRecording;
  final VoidCallback onStopRecording;
  final VoidCallback onCancelRecording;

  const VoiceInputBar({
    Key? key,
    required this.isRecording,
    required this.isEnabled,
    required this.onStartRecording,
    required this.onStopRecording,
    required this.onCancelRecording,
  }) : super(key: key);

  @override
  State<VoiceInputBar> createState() => _VoiceInputBarState();
}

class _VoiceInputBarState extends State<VoiceInputBar>
    with SingleTickerProviderStateMixin {
  Timer? _recordingTimer;
  int _recordingSeconds = 0;
  late AnimationController _waveAnimationController;

  @override
  void initState() {
    super.initState();
    _waveAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _recordingTimer?.cancel();
    _waveAnimationController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(VoiceInputBar oldWidget) {
    super.didUpdateWidget(oldWidget);

    // 录音状态变化时处理计时器
    if (widget.isRecording && !oldWidget.isRecording) {
      _startTimer();
    } else if (!widget.isRecording && oldWidget.isRecording) {
      _stopTimer();
    }
  }

  void _startTimer() {
    _recordingSeconds = 0;
    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _recordingSeconds++;
      });
    });
  }

  void _stopTimer() {
    _recordingTimer?.cancel();
    _recordingTimer = null;
    setState(() {
      _recordingSeconds = 0;
    });
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    if (widget.isRecording) {
      // 录音状态: 取消按钮 + 波形 + 时长 + 发送按钮
      return _buildRecordingState();
    } else {
      // 默认状态: 大的语音按钮
      return _buildDefaultState();
    }
  }

  /// 构建默认状态 - 大语音按钮
  Widget _buildDefaultState() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: GestureDetector(
        onTap: widget.isEnabled ? widget.onStartRecording : null,
        child: Container(
          height: 44,
          decoration: BoxDecoration(
            color: widget.isEnabled
                ? Colors.white
                : Colors.grey.shade200,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
              color: Colors.grey.shade300,
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.mic,
                color: widget.isEnabled
                    ? const Color(0xFF00d4aa)
                    : Colors.grey.shade400,
                size: 20,
              ),
              const SizedBox(width: 10),
              Text(
                '点击说话',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: widget.isEnabled
                      ? const Color(0xFF2D3436)
                      : Colors.grey.shade400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建录音状态 - 取消 + 波形 + 时长 + 发送
  Widget _buildRecordingState() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          // 取消按钮
          GestureDetector(
            onTap: widget.onCancelRecording,
            child: Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.grey.shade300,
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.close,
                color: Color(0xFF2D3436),
                size: 18,
              ),
            ),
          ),

          const SizedBox(width: 10),

          // 波形 + 时长区域
          Expanded(
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: const Color(0xFFE8F5E9),
                borderRadius: BorderRadius.circular(22),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  // 波形动画
                  Expanded(
                    child: _buildWaveform(),
                  ),
                  const SizedBox(width: 10),
                  // 时长显示
                  Text(
                    _formatDuration(_recordingSeconds),
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF4CAF50),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(width: 10),

          // 发送按钮
          GestureDetector(
            onTap: widget.onStopRecording,
            child: Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(
                color: Color(0xFF4CAF50),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// 构建波形动画
  Widget _buildWaveform() {
    return AnimatedBuilder(
      animation: _waveAnimationController,
      builder: (context, child) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: List.generate(7, (index) {
            final height = 6 +
                16 *
                    ((index % 3 == 0)
                        ? _waveAnimationController.value
                        : (1 - _waveAnimationController.value));
            return Container(
              width: 2.5,
              height: height,
              margin: const EdgeInsets.symmetric(horizontal: 1.5),
              decoration: BoxDecoration(
                color: const Color(0xFF4CAF50),
                borderRadius: BorderRadius.circular(1.5),
              ),
            );
          }),
        );
      },
    );
  }
}
