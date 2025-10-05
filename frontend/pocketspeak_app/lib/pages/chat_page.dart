import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/voice_service.dart';
import '../services/audio_player_service.dart';

class ChatMessage {
  final String messageId;
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final bool hasAudio;
  final String? audioUrl;
  final String? audioData;  // Base64编码的音频数据

  ChatMessage({
    required this.messageId,
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.hasAudio = false,
    this.audioUrl,
    this.audioData,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      messageId: json['message_id'] ?? '',
      text: json['user_text'] ?? json['ai_text'] ?? '',
      isUser: json['user_text'] != null,
      timestamp: DateTime.parse(json['timestamp']),
      hasAudio: json['has_audio'] ?? false,
      audioData: json['audio_data'],  // 获取Base64音频数据
    );
  }
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

  // 服务实例
  final VoiceService _voiceService = VoiceService();
  final ApiService _apiService = ApiService();
  final AudioPlayerService _audioPlayerService = AudioPlayerService();

  // 状态管理
  bool _isSessionInitialized = false;
  bool _isRecording = false;
  bool _isProcessing = false;
  String _listeningText = "";
  String _sessionState = "idle";

  // 动画控制器
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late AnimationController _typingController;
  late Animation<double> _typingAnimation;

  // 轮询定时器
  Timer? _statusPollingTimer;

  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _initializeVoiceSession();
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

  /// 初始化语音会话
  Future<void> _initializeVoiceSession() async {
    try {
      print('🚀 开始初始化语音会话...');

      // 显示加载提示
      setState(() {
        _isProcessing = true;
        _listeningText = "正在初始化语音会话...";
      });

      // 初始化语音会话
      final result = await _voiceService.initSession(
        autoPlayTts: false,  // 前端播放音频,后端不播放
        saveConversation: true,
        enableEchoCancellation: true,
      );

      if (result['success'] == true) {
        setState(() {
          _isSessionInitialized = true;
          _sessionState = result['state'] ?? 'ready';
          _isProcessing = false;
          _listeningText = "";
        });

        print('✅ 语音会话初始化成功: ${result['session_id']}');

        // 加载欢迎消息
        _addWelcomeMessage();

        // 启动状态轮询
        _startStatusPolling();
      } else {
        setState(() {
          _isProcessing = false;
          _listeningText = "";
        });

        // 显示错误提示
        _showErrorDialog('初始化失败', result['message'] ?? '无法初始化语音会话');
      }
    } catch (e) {
      print('❌ 初始化语音会话异常: $e');
      setState(() {
        _isProcessing = false;
        _listeningText = "";
      });

      _showErrorDialog('初始化异常', '初始化语音会话时发生错误: $e');
    }
  }

  /// 启动状态轮询（监听AI响应）
  void _startStatusPolling() {
    // 每2秒查询一次会话状态
    _statusPollingTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (!_isSessionInitialized) {
        timer.cancel();
        return;
      }

      // 查询对话历史，获取新消息
      final historyResult = await _voiceService.getConversationHistory(limit: 1);

      if (historyResult['success'] == true) {
        final messages = historyResult['messages'] as List;

        // 如果有新消息且是AI回复，添加到消息列表
        if (messages.isNotEmpty) {
          final latestMessage = messages.first;
          final messageId = latestMessage['message_id'];

          // 检查是否已存在
          final exists = _messages.any((msg) => msg.messageId == messageId);

          if (!exists && latestMessage['ai_text'] != null) {
            final aiMessage = ChatMessage.fromJson(latestMessage);

            setState(() {
              _messages.add(aiMessage);
              _isProcessing = false;
            });

            _typingController.stop();
            _scrollToBottom();

            // 如果有音频数据，自动播放
            if (aiMessage.hasAudio && aiMessage.audioData != null) {
              print('🔊 检测到AI音频回复，准备播放...');
              _audioPlayerService.playBase64Audio(
                aiMessage.audioData!,
                audioId: aiMessage.messageId,
              ).then((success) {
                if (success) {
                  print('✅ AI音频播放成功');
                } else {
                  print('❌ AI音频播放失败');
                }
              });
            }
          }
        }
      }

      // 更新会话状态
      final statusResult = await _voiceService.getSessionStatus();
      if (statusResult['success'] == true) {
        setState(() {
          _sessionState = statusResult['data']?['state'] ?? _sessionState;
        });
      }
    });
  }

  void _addWelcomeMessage() {
    setState(() {
      _messages.add(ChatMessage(
        messageId: 'welcome_${DateTime.now().millisecondsSinceEpoch}',
        text: "你好！我是小智AI，你的英语学习伙伴。让我们开始一段有趣的英语对话吧！🎯",
        isUser: false,
        timestamp: DateTime.now(),
        hasAudio: false,
      ));
    });
    _scrollToBottom();
  }

  /// 开始语音录音
  Future<void> _startVoiceRecording() async {
    if (_isRecording || _isProcessing || !_isSessionInitialized) {
      print('⚠️ 无法开始录音: isRecording=$_isRecording, isProcessing=$_isProcessing, isInitialized=$_isSessionInitialized');
      return;
    }

    try {
      setState(() {
        _listeningText = "正在连接...";
      });

      // 调用后端开始录音API
      final result = await _voiceService.startRecording();

      if (result['success'] == true) {
        setState(() {
          _isRecording = true;
          _listeningText = "正在听您说话...";
          _sessionState = result['state'] ?? _sessionState;
        });

        _pulseController.repeat(reverse: true);
        print('🎤 开始录音');
      } else {
        setState(() {
          _listeningText = "";
        });
        _showSnackBar('无法开始录音: ${result['message']}');
      }
    } catch (e) {
      print('❌ 开始录音异常: $e');
      setState(() {
        _listeningText = "";
      });
      _showSnackBar('开始录音失败: $e');
    }
  }

  /// 停止语音录音
  Future<void> _stopVoiceRecording() async {
    if (!_isRecording) return;

    try {
      // 调用后端停止录音API
      final result = await _voiceService.stopRecording();

      setState(() {
        _isRecording = false;
        _listeningText = result['success'] == true ? "正在处理..." : "";
        _sessionState = result['state'] ?? _sessionState;
      });

      _pulseController.stop();
      print('⏹️ 停止录音');

      if (result['success'] == true) {
        // 开始等待AI响应
        setState(() {
          _isProcessing = true;
        });
        _typingController.repeat();
      } else {
        _showSnackBar('停止录音失败: ${result['message']}');
      }
    } catch (e) {
      print('❌ 停止录音异常: $e');
      setState(() {
        _isRecording = false;
        _listeningText = "";
      });
      _pulseController.stop();
      _showSnackBar('停止录音失败: $e');
    }
  }

  /// 发送文本消息
  Future<void> _sendTextMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty || !_isSessionInitialized) return;

    try {
      // 添加用户消息到UI
      setState(() {
        _messages.add(ChatMessage(
          messageId: 'user_${DateTime.now().millisecondsSinceEpoch}',
          text: text,
          isUser: true,
          timestamp: DateTime.now(),
        ));
        _isProcessing = true;
      });

      _textController.clear();
      _scrollToBottom();
      _typingController.repeat();

      // 调用后端发送文本API
      final result = await _voiceService.sendTextMessage(text);

      if (result['success'] == true) {
        setState(() {
          _sessionState = result['state'] ?? _sessionState;
        });
        print('💬 文本消息已发送: $text');
        // AI响应会通过状态轮询自动添加
      } else {
        setState(() {
          _isProcessing = false;
        });
        _typingController.stop();
        _showSnackBar('发送消息失败: ${result['message']}');
      }
    } catch (e) {
      print('❌ 发送文本消息异常: $e');
      setState(() {
        _isProcessing = false;
      });
      _typingController.stop();
      _showSnackBar('发送消息失败: $e');
    }
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

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _showErrorDialog(String title, String message) {
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _statusPollingTimer?.cancel();
    _pulseController.dispose();
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    _audioPlayerService.dispose();

    // 关闭语音会话
    _voiceService.closeSession();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1a1a2e),
      body: Stack(
        children: [
          // 全屏模型展示区域
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
                  // AI角色展示区域
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
                    _isSessionInitialized
                        ? '英语学习伙伴 • ${_getStateText()}'
                        : '正在初始化...',
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

          // 聊天消息区域
          Positioned(
            left: 4,
            right: 4,
            bottom: 60,
            child: Container(
              height: 320,
              decoration: BoxDecoration(
                color: Colors.transparent,
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

          // 输入区域
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

  String _getStateText() {
    switch (_sessionState) {
      case 'listening':
        return '正在听';
      case 'processing':
        return '正在思考';
      case 'speaking':
        return '正在说话';
      case 'ready':
        return '就绪';
      default:
        return '在线';
    }
  }

  Widget _buildChatList() {
    return Container(
      padding: const EdgeInsets.only(left: 16, right: 16, top: 6, bottom: 4),
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
      margin: const EdgeInsets.symmetric(vertical: 4),
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
                        colors: [Color(0xFF00d4aa), Color(0xFF00c4a7)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: message.isUser ? null : Colors.white,
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

  Widget _buildTypingIndicator() {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
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
        top: 4,
        bottom: MediaQuery.of(context).padding.bottom - 8,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
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
              padding: const EdgeInsets.all(8),
              margin: const EdgeInsets.only(bottom: 8),
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

          // 输入区域
          Container(
            padding: const EdgeInsets.only(left: 4, right: 4, top: 14, bottom: 6),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              children: [
                // 语音按钮
                GestureDetector(
                  onLongPressStart: (_) => _startVoiceRecording(),
                  onLongPressEnd: (_) => _stopVoiceRecording(),
                  onTap: () {
                    // 点击切换录音状态：未录音时开始，录音中时停止
                    if (_isRecording) {
                      _stopVoiceRecording();
                    } else {
                      _startVoiceRecording();
                    }
                  },
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
                                : (_isSessionInitialized
                                    ? const Color(0xFF00d4aa)
                                    : const Color(0xFFCCCCCC)),
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

                // 输入框
                Expanded(
                  child: Container(
                    height: 36,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF5F5F5),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: TextField(
                      controller: _textController,
                      enabled: _isSessionInitialized,
                      textAlign: TextAlign.left,
                      decoration: const InputDecoration(
                        hintText: '请输入文本...',
                        hintStyle: TextStyle(
                          color: Color(0xFF999999),
                          fontSize: 14,
                        ),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                      ),
                      style: const TextStyle(
                        fontSize: 14,
                        color: Color(0xFF2D3436),
                      ),
                      textAlignVertical: TextAlignVertical.center,
                      onSubmitted: (_) => _sendTextMessage(),
                      onChanged: (text) {
                        setState(() {});
                      },
                    ),
                  ),
                ),

                const SizedBox(width: 8),

                // 发送按钮
                GestureDetector(
                  onTap: _textController.text.trim().isNotEmpty && _isSessionInitialized
                      ? _sendTextMessage
                      : null,
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: _textController.text.trim().isNotEmpty && _isSessionInitialized
                          ? const Color(0xFF667EEA)
                          : const Color(0xFFCCCCCC),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: const Icon(
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
