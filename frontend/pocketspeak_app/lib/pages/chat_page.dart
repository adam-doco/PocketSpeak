import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final bool hasAudio;
  final String? audioUrl;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.hasAudio = false,
    this.audioUrl,
  });
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage>
    with TickerProviderStateMixin {
  final List<ChatMessage> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  bool _isRecording = false;
  bool _isProcessing = false;
  String _listeningText = "";

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late AnimationController _typingController;
  late Animation<double> _typingAnimation;

  final ApiService _apiService = ApiService(); // TODO: 将在后续集成真实API时使用

  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _addWelcomeMessage();
  }

  void _setupAnimations() {
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    _typingController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _typingAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _typingController,
      curve: Curves.easeInOut,
    ));
  }

  void _addWelcomeMessage() {
    setState(() {
      _messages.add(ChatMessage(
        text: "你好！我是小智AI，你的英语学习伙伴。让我们开始一段有趣的英语对话吧！🎯",
        isUser: false,
        timestamp: DateTime.now(),
        hasAudio: false,
      ));
    });
    _scrollToBottom();
  }

  Future<void> _startVoiceRecording() async {
    if (_isRecording || _isProcessing) return;

    setState(() {
      _isRecording = true;
      _listeningText = "正在听您说话...";
    });

    _pulseController.repeat(reverse: true);

    // 模拟语音识别过程
    await Future.delayed(const Duration(seconds: 2));

    // 模拟识别结果
    const recognizedText = "Hello, how are you today?";

    setState(() {
      _isRecording = false;
      _listeningText = "";
    });

    _pulseController.stop();

    _addUserMessage(recognizedText);
    _processAIResponse(recognizedText);
  }

  void _stopVoiceRecording() {
    if (!_isRecording) return;

    setState(() {
      _isRecording = false;
      _listeningText = "";
    });

    _pulseController.stop();
  }

  void _addUserMessage(String text) {
    setState(() {
      _messages.add(ChatMessage(
        text: text,
        isUser: true,
        timestamp: DateTime.now(),
      ));
    });
    _scrollToBottom();
  }

  Future<void> _processAIResponse(String userMessage) async {
    setState(() {
      _isProcessing = true;
    });

    _typingController.repeat();

    // 模拟AI响应延迟
    await Future.delayed(const Duration(seconds: 3));

    // 模拟AI回复
    const aiResponse = "I'm doing great, thank you for asking! How about you? What would you like to practice today? 😊";

    setState(() {
      _isProcessing = false;
      _messages.add(ChatMessage(
        text: aiResponse,
        isUser: false,
        timestamp: DateTime.now(),
        hasAudio: true,
        audioUrl: "mock_audio_url",
      ));
    });

    _typingController.stop();
    _scrollToBottom();
  }

  void _sendTextMessage() {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    _addUserMessage(text);
    _textController.clear();
    _processAIResponse(text);
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final screenHeight = screenSize.height;

    return Scaffold(
      backgroundColor: const Color(0xFF1a1a2e), // 深色背景模拟模型展示区
      body: Stack(
        children: [
          // 全屏模型展示区域 (目前用渐变背景模拟)
          Container(
            width: double.infinity,
            height: double.infinity,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF1a1a2e),
                  Color(0xFF16213e),
                  Color(0xFF0f3460),
                ],
              ),
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // 模拟AI角色展示区域
                  Container(
                    width: 200,
                    height: 200,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF667EEA), Color(0xFF764BA2)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(100),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF667EEA).withValues(alpha: 0.3),
                          blurRadius: 30,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.psychology_outlined,
                      size: 80,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    '小智AI',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '英语学习伙伴',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.white.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 返回按钮
          Positioned(
            top: MediaQuery.of(context).padding.top + 10,
            left: 16,
            child: GestureDetector(
              onTap: () => Navigator.of(context).pop(),
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(
                  Icons.arrow_back_ios_new,
                  color: Colors.white,
                  size: 20,
                ),
              ),
            ),
          ),

          // 聊天消息区域 (扩展到输入区上方)
          Positioned(
            left: 4, // 减少左边距
            right: 4, // 减少右边距
            bottom: 60, // 进一步向下扩展，减少与输入区间距
            child: Container(
              height: 320, // 向上扩展20px，从240改为260
              decoration: BoxDecoration(
                color: Colors.transparent, // 100%透明
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.1),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: _buildChatList(),
            ),
          ),

          // 输入区域 (完全贴底部，无SafeArea)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _buildInputArea(),
          ),
        ],
      ),
    );
  }

  Widget _buildChatList() {
    return Container(
      padding: const EdgeInsets.only(left: 16, right: 16, top: 6, bottom: 4), // 减少底部内边距
      child: ListView.builder(
        controller: _scrollController,
        itemCount: _messages.length + (_isProcessing ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == _messages.length && _isProcessing) {
            return _buildTypingIndicator();
          }

          final message = _messages[index];
          return _buildMessageBubble(message);
        },
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4), // 缩小气泡间距
      child: Row(
        mainAxisAlignment: message.isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        children: [
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.7,
              ),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: message.isUser
                    ? const LinearGradient(
                        colors: [Color(0xFF00d4aa), Color(0xFF00c4a7)], // Zoe的绿色渐变
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: message.isUser ? null : Colors.white, // AI消息白色背景
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(message.isUser ? 16 : 4),
                  bottomRight: Radius.circular(message.isUser ? 4 : 16),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.08),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Text(
                message.text,
                style: TextStyle(
                  fontSize: 14,
                  color: message.isUser ? Colors.white : const Color(0xFF2D3436),
                  height: 1.4,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAudioPlayer() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F9FA),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          GestureDetector(
            onTap: () {
              // TODO: 实现音频播放
            },
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: const Color(0xFF667EEA),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(
                Icons.play_arrow,
                color: Colors.white,
                size: 18,
              ),
            ),
          ),
          const SizedBox(width: 8),
          const Text(
            '点击播放语音',
            style: TextStyle(
              fontSize: 12,
              color: Color(0xFF636E72),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4), // 缩小气泡间距
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomRight: Radius.circular(16),
                bottomLeft: Radius.circular(4),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.08),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: AnimatedBuilder(
              animation: _typingAnimation,
              builder: (context, child) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildTypingDot(0),
                    const SizedBox(width: 4),
                    _buildTypingDot(1),
                    const SizedBox(width: 4),
                    _buildTypingDot(2),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypingDot(int index) {
    final delay = index * 0.3;
    final animationValue = (_typingAnimation.value - delay).clamp(0.0, 1.0);
    final opacity = (sin(animationValue * pi * 2) + 1) / 2;

    return Container(
      width: 6,
      height: 6,
      decoration: BoxDecoration(
        color: Color(0xFF667EEA).withValues(alpha: 0.3 + opacity * 0.7),
        borderRadius: BorderRadius.circular(3),
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 4,  // 恢复原来的顶部间距
        bottom: MediaQuery.of(context).padding.bottom - 8, // 大幅减少底部间距，缩短背景
      ),
      decoration: BoxDecoration(
        color: Colors.white, // 改为纯白色背景
        // 完全移除圆角，直接贴底
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 15,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: Column(
        children: [
          // 录音状态提示
          if (_isRecording || _listeningText.isNotEmpty) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(8), // 从12改为8
              margin: const EdgeInsets.only(bottom: 8), // 从12改为8
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF00d4aa).withValues(alpha: 0.1),
                    const Color(0xFF00c4a7).withValues(alpha: 0.1),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFF00d4aa).withValues(alpha: 0.3),
                ),
              ),
              child: Row(
                children: [
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _pulseAnimation.value,
                        child: Container(
                          width: 16,
                          height: 16,
                          decoration: BoxDecoration(
                            color: const Color(0xFF00d4aa),
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(width: 12),
                  Text(
                    _listeningText,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Color(0xFF00d4aa),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],

          // 统一的输入区域背景
          Container(
            padding: const EdgeInsets.only(left: 4, right: 4, top: 14, bottom: 6), // 再增加6px，从8改为14
            decoration: BoxDecoration(
              color: Colors.white, // 改为白色背景
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              children: [
                // 语音按钮 - 无独立背景
                GestureDetector(
                  onLongPressStart: (_) => _startVoiceRecording(),
                  onLongPressEnd: (_) => _stopVoiceRecording(),
                  onTap: _startVoiceRecording,
                  child: AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _isRecording ? _pulseAnimation.value : 1.0,
                        child: Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: _isRecording
                                ? const Color(0xFFE74C3C)
                                : const Color(0xFF00d4aa), // 纯绿色
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Icon(
                            _isRecording ? Icons.stop : Icons.mic,
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                      );
                    },
                  ),
                ),

                const SizedBox(width: 8),

                // 输入框 - 扁平设计
                Expanded(
                  child: Container(
                    height: 36,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF5F5F5), // 改为浅灰色
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: TextField(
                      controller: _textController,
                      textAlign: TextAlign.left, // 确保文字左对齐
                      decoration: const InputDecoration(
                        hintText: '请输入文本...',
                        hintStyle: TextStyle(
                          color: Color(0xFF999999),
                          fontSize: 14,
                        ),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10, // 调整垂直居中
                        ),
                      ),
                      style: const TextStyle(
                        fontSize: 14,
                        color: Color(0xFF2D3436),
                      ),
                      textAlignVertical: TextAlignVertical.center, // 垂直居中
                      onSubmitted: (_) => _sendTextMessage(),
                      onChanged: (text) {
                        setState(() {}); // 触发重建以更新发送按钮状态
                      },
                    ),
                  ),
                ),

                const SizedBox(width: 8),

                // 发送按钮 - 无独立背景
                GestureDetector(
                  onTap: _textController.text.trim().isNotEmpty ? _sendTextMessage : null,
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: _textController.text.trim().isNotEmpty
                          ? const Color(0xFF667EEA) // 纯紫色
                          : const Color(0xFFCCCCCC), // 禁用状态灰色
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Icon(
                      Icons.send,
                      color: Colors.white,
                      size: 18,
                    ),
                  ),
                ),
              ],
            ),
          ),

        ],
      ),
    );
  }
}