import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import '../services/api_service.dart';
import '../services/voice_service.dart';
import '../services/audio_player_service.dart';
import '../services/seamless_audio_player.dart';  // 🚀 无缝音频播放器（借鉴Zoev4架构）
import '../widgets/live2d_widget.dart';  // 🎭 Live2D模型组件
import '../services/motion_controller.dart';  // 🎭 动作播放控制器
import '../services/lip_sync_controller.dart';  // 👄 嘴部同步控制器

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
  // 🔧 日志开关（生产环境设为false）
  static const bool _enableDebugLogs = true;

  final List<ChatMessage> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  // 服务实例
  final VoiceService _voiceService = VoiceService();
  final ApiService _apiService = ApiService();
  final AudioPlayerService _audioPlayerService = AudioPlayerService();
  final SeamlessAudioPlayer _streamingPlayer = SeamlessAudioPlayer();  // 🚀 无缝音频播放器

  // 状态管理
  bool _isSessionInitialized = false;
  bool _isRecording = false;
  bool _isProcessing = false;
  String _listeningText = "";
  String _sessionState = "idle";
  bool _useStreamingPlayback = false;  // 🚀 是否使用流式播放（WebSocket推送）

  // 动画控制器
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late AnimationController _typingController;
  late Animation<double> _typingAnimation;

  // Live2D控制器
  Live2DController? _live2dController;

  // 🎭 表情控制器
  MotionController? _motionController;
  LipSyncController? _lipSyncController;

  // ❌ 删除旧逻辑: 不再使用轮询和逐句播放队列
  // Timer? _statusPollingTimer;
  // Timer? _sentencePollingTimer;
  // int _lastSentenceIndex = 0;
  // List<Map<String, String>> _sentenceQueue = [];
  // bool _isPlayingSentences = false;
  // bool _isPolling = false;
  // StreamSubscription? _playbackSubscription;
  // String? _lastProcessedMessageId;

  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _initializeVoiceSession();
  }

  /// 🚀 设置WebSocket回调（模仿py-xiaozhi的即时播放）
  void _setupWebSocketCallbacks() {
    // 收到音频帧立即播放
    _voiceService.onAudioFrameReceived = (String base64Data) {
      // ✅ 精简日志：删除高频音频帧日志
      _streamingPlayer.addAudioFrame(base64Data);
    };

    // 收到用户语音识别文字
    _voiceService.onUserTextReceived = (String text) {
      _debugLog('📝 收到用户文字: $text');

      if (_useStreamingPlayback) {
        setState(() {
          final userMessage = ChatMessage(
            messageId: 'user_${DateTime.now().millisecondsSinceEpoch}',
            text: text,
            isUser: true,
            timestamp: DateTime.now(),
          );
          _messages.add(userMessage);
        });
        _scrollToBottom();
      }
    };

    // 收到AI文本立即显示
    _voiceService.onTextReceived = (String text) {
      _debugLog('📝 收到AI文本: $text');

      // 🚀 只在流式模式下显示（避免与轮询重复）
      if (_useStreamingPlayback) {
        setState(() {
          final aiMessage = ChatMessage(
            messageId: 'ai_${DateTime.now().millisecondsSinceEpoch}',
            text: text,
            isUser: false,
            timestamp: DateTime.now(),
            hasAudio: false,  // 音频通过流式播放，不需要关联
          );
          _messages.add(aiMessage);
          _isProcessing = false;
        });
        _typingController.stop();
        _scrollToBottom();
      }
    };

    // 🎭 收到AI表情emoji
    _voiceService.onEmotionReceived = (String emoji) {
      _debugLog('🎭 收到emotion: $emoji');

      // 播放对应的表情和动作
      if (_motionController != null) {
        _motionController!.playEmotionByEmoji(emoji);
      } else {
        _debugLog('⚠️ MotionController未初始化，无法播放表情');
      }
    };

    // 状态变化
    _voiceService.onStateChanged = (String state) {
      _debugLog('🔄 状态: $state');

      // 🔥 关键修复：模拟 py-xiaozhi 的 clear_audio_queue()
      // 当用户开始新的录音（listening）时，清空上一轮的播放列表
      // 这确保每次对话都从索引0开始，不会累积
      if (state == 'listening' && _sessionState != 'listening') {
        _streamingPlayer.stop();

        // 👄 停止嘴部同步动画
        _lipSyncController?.stopLipSync();
      }

      // 👄 根据状态控制嘴部同步
      if (state == 'speaking' && _sessionState != 'speaking') {
        // AI开始说话，启动嘴部同步
        _lipSyncController?.startLipSync();
      } else if (state != 'speaking' && _sessionState == 'speaking') {
        // AI停止说话，停止嘴部同步
        _lipSyncController?.stopLipSync();
      }

      setState(() {
        _sessionState = state;
      });
    };
  }

  /// 统一的日志输出方法
  void _debugLog(String message) {
    if (_enableDebugLogs) {
      print(message);
    }
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
      // ✅ 精简：移除初始化日志

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

        // ✅ 精简：移除成功日志

        // 🚀 连接WebSocket接收实时音频推送
        final wsConnected = await _voiceService.connectWebSocket();
        if (wsConnected) {
          // ✅ 连接成功后再设置回调，避免被清空
          _setupWebSocketCallbacks();

          setState(() {
            _useStreamingPlayback = true;  // 启用流式播放
          });
          // ✅ 精简：移除WebSocket连接成功日志
        } else {
          _debugLog('⚠️ WebSocket连接失败');
        }

        // 加载欢迎消息
        _addWelcomeMessage();

        // ❌ 删除旧逻辑: 不再启动状态轮询，完全依赖WebSocket推送
        // _startStatusPolling();
      } else {
        setState(() {
          _isProcessing = false;
          _listeningText = "";
        });

        // 显示错误提示
        _showErrorDialog('初始化失败', result['message'] ?? '无法初始化语音会话');
      }
    } catch (e) {
      _debugLog('❌ 初始化异常: $e');
      setState(() {
        _isProcessing = false;
        _listeningText = "";
      });

      _showErrorDialog('初始化异常', '初始化语音会话时发生错误: $e');
    }
  }

  /// ❌ 删除旧逻辑: 不再轮询检查新消息，完全依赖WebSocket推送
  /*
  Future<void> _checkForNewMessages() async {
    // ⚠️ 注意：AI消息现在通过逐句播放机制实时显示，不再从历史记录获取
    // 但需要从历史记录获取用户语音识别的文字

    // 查询对话历史，获取新消息
    final historyResult = await _voiceService.getConversationHistory(limit: 1);

    if (historyResult['success'] == true) {
      final messages = historyResult['messages'] as List;

      if (messages.isEmpty) {
        return; // 静默返回，减少日志噪音
      }

      // 检查是否有用户文字需要显示（语音识别结果）
      if (messages.isNotEmpty) {
        final latestMessage = messages.first;
        final messageId = latestMessage['message_id'] as String?;

        // ✅ 关键修复：通过message_id判断是否已处理，避免重复添加
        if (messageId != null &&
            messageId != _lastProcessedMessageId &&
            latestMessage['user_text'] != null) {
          final userText = latestMessage['user_text'] as String;

          setState(() {
            _messages.add(ChatMessage(
              messageId: messageId,
              text: userText,
              isUser: true,
              timestamp: DateTime.now(),
            ));
          });

          // 记录已处理的消息ID
          _lastProcessedMessageId = messageId;
          _scrollToBottom();

          // ✅ 只在实际添加用户消息时打印日志
          _debugLog('✅ 添加用户语音识别文字: $userText (message_id: $messageId)');
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
  }
  */

  /// ❌ 删除旧逻辑: 不再轮询状态
  /*
  void _startStatusPolling() {
    _statusPollingTimer = Timer.periodic(const Duration(milliseconds: 300), (timer) async {
      if (!_isSessionInitialized) {
        timer.cancel();
        return;
      }
      await _checkForNewMessages();
    });
  }
  */

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
      // ✅ 精简：移除无法录音的警告日志
      return;
    }

    try {
      // ✅ 精简：移除时间戳日志

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
        // ✅ 精简：移除开始录音日志
      } else {
        setState(() {
          _listeningText = "";
        });
        _showSnackBar('无法开始录音: ${result['message']}');
      }
    } catch (e) {
      _debugLog('❌ 开始录音异常: $e');
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
      // ✅ 精简：移除时间戳日志

      // 调用后端停止录音API
      final result = await _voiceService.stopRecording();
      // ✅ 精简：移除耗时日志

      setState(() {
        _isRecording = false;
        _listeningText = result['success'] == true ? "正在处理..." : "";
        _sessionState = result['state'] ?? _sessionState;
      });

      _pulseController.stop();
      // ✅ 精简：移除停止录音日志

      if (result['success'] == true) {
        // 开始等待AI响应
        setState(() {
          _isProcessing = true;
        });
        _typingController.repeat();

        // ❌ 删除旧逻辑: 完全使用WebSocket流式播放，不再轮询
        // ✅ 精简：移除流式播放日志
      } else {
        _showSnackBar('停止录音失败: ${result['message']}');
      }
    } catch (e) {
      _debugLog('❌ 停止录音异常: $e');
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
        // ✅ 精简：移除发送成功日志
        // AI响应会通过状态轮询自动添加
      } else {
        setState(() {
          _isProcessing = false;
        });
        _typingController.stop();
        _showSnackBar('发送消息失败: ${result['message']}');
      }
    } catch (e) {
      _debugLog('❌ 发送文本消息异常: $e');
      setState(() {
        _isProcessing = false;
      });
      _typingController.stop();
      _showSnackBar('发送消息失败: $e');
    }
  }

  void _scrollToBottom() {
    // 使用Future.delayed确保在Widget完全渲染后滚动
    // 这样可以获取正确的maxScrollExtent
    Future.delayed(const Duration(milliseconds: 100), () {
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

  /// ❌ 删除旧逻辑: 不再使用逐句播放轮询
  /*
  void _startSentencePlayback() {
    print('🎵 启动逐句播放轮询...');

    _lastSentenceIndex = 0;
    _sentenceQueue.clear();
    _isPlayingSentences = false;  // ✅ 初始化为false,允许第一句开始播放

    // 每40ms轮询新完成的句子（降低延迟）
    _sentencePollingTimer = Timer.periodic(const Duration(milliseconds: 40), (timer) async {
      // 🔒 防止并发轮询
      if (_isPolling) return;
      _isPolling = true;

      try {
        final result = await _voiceService.getCompletedSentences(
          lastSentenceIndex: _lastSentenceIndex,
        );

        if (result['success'] == true) {
          final data = result['data'];
          final hasNewSentences = data['has_new_sentences'] ?? false;
          final isComplete = data['is_complete'] ?? false;

          if (hasNewSentences) {
            final sentences = data['sentences'] as List<dynamic>;

            for (var sentence in sentences) {
              final text = sentence['text'] as String;
              final audioData = sentence['audio_data'] as String;

              _debugLog('📝 收到新句子: $text');

              // ✅ 每句话创建一个独立的AI消息气泡
              final aiMessage = ChatMessage(
                messageId: 'ai_${DateTime.now().millisecondsSinceEpoch}',
                text: text,  // ✅ 只显示当前句子，不累积
                isUser: false,
                timestamp: DateTime.now(),
                hasAudio: true,
              );

              setState(() {
                _messages.add(aiMessage);
                _isProcessing = false;
              });

              _typingController.stop();
              _scrollToBottom();

              _debugLog('✅ 创建AI消息气泡: $text');

              // 添加到播放队列
              _sentenceQueue.add({
                'text': text,
                'audioData': audioData,
              });
            }

            // 更新索引
            _lastSentenceIndex = data['total_sentences'];

            // 立即启动播放（无论是否正在播放，新句子加入队列后会自动续播）
            if (!_isPlayingSentences) {
              _playNextSentence();
            }
          }

          // TTS完成,停止轮询
          if (isComplete) {
            _debugLog('🛑 TTS完成,停止句子轮询');
            timer.cancel();
            _sentencePollingTimer = null;
          }
        }
      } catch (e) {
        _debugLog('❌ 获取句子失败: $e');
      } finally {
        _isPolling = false;  // 🔓 释放锁
      }
    });
  }

  /// 播放下一句
  void _playNextSentence() async {
    if (_sentenceQueue.isEmpty) {
      _debugLog('✅ 句子队列已空,播放完成');
      _isPlayingSentences = false;
      return;
    }

    _isPlayingSentences = true;
    final sentence = _sentenceQueue.removeAt(0);
    final text = sentence['text']!;
    final audioData = sentence['audioData']!;

    _debugLog('🔊 开始播放句子: $text');

    final playSuccess = await _audioPlayerService.playBase64Audio(
      audioData,
      audioId: 'sentence_${DateTime.now().millisecondsSinceEpoch}',
    );

    if (playSuccess) {
      // 监听播放完成,播放下一句
      _waitForPlaybackEnd();
    } else {
      _debugLog('❌ 播放失败,继续下一句');
      _playNextSentence();
    }
  }

  /// 等待当前句子播放完成
  void _waitForPlaybackEnd() {
    // 取消之前的监听器(如果存在)
    _playbackSubscription?.cancel();

    // 监听音频播放器的状态流,等待播放完成
    _playbackSubscription = _audioPlayerService.playerStateStream.listen((state) {
      // 当播放完成时,播放下一句
      if (state.processingState == ProcessingState.completed) {
        _debugLog('✅ 句子播放完成,播放下一句');
        _playbackSubscription?.cancel();
        _playNextSentence();
      }
    });
  }

  */

  @override
  void dispose() {
    // ❌ 删除旧逻辑: 不再使用轮询
    // _statusPollingTimer?.cancel();
    // _sentencePollingTimer?.cancel();
    // _playbackSubscription?.cancel();

    _pulseController.dispose();
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();

    // 🎭 清理表情控制器
    _lipSyncController?.dispose();

    // 🚀 清理WebSocket和流式播放器
    _voiceService.disconnectWebSocket();
    _streamingPlayer.dispose();

    // 关闭语音会话
    _voiceService.closeSession();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,  // 纯黑色背景
      body: Stack(
        children: [
          // 🎭 Live2D模型背景层（最底层）
          Positioned.fill(
            child: Container(
              color: Colors.black,  // 纯黑色背景
              child: Live2DWidget(
                onControllerCreated: (controller) {
                  setState(() {
                    _live2dController = controller;
                    // 初始化表情控制器
                    _motionController = MotionController(controller);
                    _lipSyncController = LipSyncController(controller);
                  });
                  // ✅ 精简：移除Live2D初始化日志
                },
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
      margin: const EdgeInsets.symmetric(vertical: 2),  // ✅ 缩短气泡间距: 4 → 2
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
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),  // ✅ 缩短内部间距: all(16) → h:12, v:8
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
                  height: 1.3,  // ✅ 缩短行高: 1.4 → 1.3
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
          // 输入区域
          Container(
            padding: const EdgeInsets.only(left: 4, right: 4, top: 10, bottom: 6),  // ✅ 降低4px: top 14 → 10
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
