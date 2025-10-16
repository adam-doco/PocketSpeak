import 'package:flutter/material.dart';
import '../widgets/live2d_widget.dart';

/// Live2D模型测试页面
class Live2DTestPage extends StatefulWidget {
  const Live2DTestPage({super.key});

  @override
  State<Live2DTestPage> createState() => _Live2DTestPageState();
}

class _Live2DTestPageState extends State<Live2DTestPage> {
  // 使用Live2DController来控制模型
  Live2DController? _live2dController;

  void _setController(Live2DController controller) {
    setState(() {
      _live2dController = controller;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Live2D 模型测试'),
        backgroundColor: const Color(0xFF6366F1),
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          // Live2D模型显示区域
          Positioned.fill(
            child: Live2DWidget(
              onControllerCreated: _setController,
            ),
          ),

          // 控制按钮
          Positioned(
            bottom: 20,
            left: 20,
            right: 20,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 所有动作按钮（6个动作）
                  Card(
                    color: Colors.white.withOpacity(0.95),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '🎬 所有动作（6个）',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _buildActionButton(
                                '0-Idle待机',
                                Colors.grey,
                                () => _live2dController?.playMotion('', 0),
                              ),
                              _buildActionButton(
                                '1-jingya惊讶',
                                Colors.orange,
                                () => _live2dController?.playMotion('', 1),
                              ),
                              _buildActionButton(
                                '2-kaixin开心',
                                Colors.pink,
                                () => _live2dController?.playMotion('', 2),
                              ),
                              _buildActionButton(
                                '3-shengqi生气',
                                Colors.red,
                                () => _live2dController?.playMotion('', 3),
                              ),
                              _buildActionButton(
                                '4-wink眨眼',
                                Colors.purple,
                                () => _live2dController?.playMotion('', 4),
                              ),
                              _buildActionButton(
                                '5-yaotou摇头',
                                Colors.blue,
                                () => _live2dController?.playMotion('', 5),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 所有表情按钮（7个表情）
                  Card(
                    color: Colors.white.withOpacity(0.95),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '😊 所有表情（7个）',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _buildExpressionButton(
                                'A1爱心眼',
                                const Color(0xFFFF69B4),
                                () => _live2dController?.playExpression('A1爱心眼'),
                              ),
                              _buildExpressionButton(
                                'A2生气',
                                const Color(0xFFFF4444),
                                () => _live2dController?.playExpression('A2生气'),
                              ),
                              _buildExpressionButton(
                                'A3星星眼',
                                const Color(0xFFFFD700),
                                () => _live2dController?.playExpression('A3星星眼'),
                              ),
                              _buildExpressionButton(
                                'A4哭哭',
                                const Color(0xFF87CEEB),
                                () => _live2dController?.playExpression('A4哭哭'),
                              ),
                              _buildExpressionButton(
                                'B1麦克风',
                                const Color(0xFF9370DB),
                                () => _live2dController?.playExpression('B1麦克风'),
                              ),
                              _buildExpressionButton(
                                'B2外套',
                                const Color(0xFF20B2AA),
                                () => _live2dController?.playExpression('B2外套'),
                              ),
                              _buildExpressionButton(
                                '舌头',
                                const Color(0xFFFF1493),
                                () => _live2dController?.playExpression('舌头'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 组合测试
                  Card(
                    color: Colors.white.withOpacity(0.95),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '🎭 组合测试（动作+表情）',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _buildComboButton(
                                '开心组合',
                                Colors.pink,
                                () async {
                                  await _live2dController?.playMotion('', 2);
                                  await _live2dController?.playExpression('A1爱心眼');
                                },
                              ),
                              _buildComboButton(
                                '惊讶组合',
                                Colors.orange,
                                () async {
                                  await _live2dController?.playMotion('', 1);
                                  await _live2dController?.playExpression('A3星星眼');
                                },
                              ),
                              _buildComboButton(
                                '生气组合',
                                Colors.red,
                                () async {
                                  await _live2dController?.playMotion('', 3);
                                  await _live2dController?.playExpression('A2生气');
                                },
                              ),
                              _buildComboButton(
                                '哭泣组合',
                                Colors.blue,
                                () async {
                                  await _live2dController?.playMotion('', 0);
                                  await _live2dController?.playExpression('A4哭哭');
                                },
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(String label, Color color, VoidCallback? onPressed) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        minimumSize: const Size(0, 42),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
      ),
    );
  }

  Widget _buildExpressionButton(String label, Color color, VoidCallback? onPressed) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        minimumSize: const Size(0, 40),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 13),
      ),
    );
  }

  Widget _buildComboButton(String label, Color color, VoidCallback? onPressed) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        minimumSize: const Size(0, 44),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
      ),
    );
  }
}
