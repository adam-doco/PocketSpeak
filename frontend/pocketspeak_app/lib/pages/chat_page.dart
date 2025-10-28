import 'dart:async';
import 'dart:math';
import 'dart:convert';  // V1.5: JSON编解码
import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';  // V1.5: 单词点击识别
import 'package:shared_preferences/shared_preferences.dart';  // V1.5: 聊天记录持久化
import '../services/api_service.dart';
import '../services/voice_service.dart';
import '../services/audio_player_service.dart';
import '../services/seamless_audio_player.dart';  // 🚀 无缝音频播放器（借鉴Zoev4架构）
import '../widgets/live2d_widget.dart';  // 🎭 Live2D模型组件
import '../services/motion_controller.dart';  // 🎭 动作播放控制器
import '../services/lip_sync_controller.dart';  // 👄 嘴部同步控制器
import '../services/word_service.dart';  // V1.5: 单词查询服务
import '../widgets/word_popup_sheet.dart';  // V1.5: 单词弹窗组件
import '../services/speech_eval_service.dart';  // V1.6: 语音评分服务
import '../models/speech_feedback.dart';  // V1.6: 语音评分数据模型
import '../widgets/speech_score_card.dart';  // V1.6: 语音评分卡片
import '../widgets/pronunciation_analysis_modal.dart';  // V1.6: 发音分析弹窗
import '../widgets/grammar_suggestion_modal.dart';  // V1.6: 语法建议弹窗
import '../widgets/expression_improvement_modal.dart';  // V1.6: 表达优化弹窗
import '../widgets/voice_input_bar.dart';  // V1.7: 优化的语音输入条

class ChatMessage {
  final String messageId;
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final bool hasAudio;
  final String? audioUrl;
  final String? audioData;  // Base64编码的音频数据
  final SpeechFeedbackResponse? speechFeedback;  // V1.6: 语音评分数据

  ChatMessage({
    required this.messageId,
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.hasAudio = false,
    this.audioUrl,
    this.audioData,
    this.speechFeedback,  // V1.6: 语音评分
  });

  // 从后端API响应创建消息
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

  // V1.5: 从本地存储加载消息
  factory ChatMessage.fromStorage(Map<String, dynamic> json) {
    return ChatMessage(
      messageId: json['messageId'] ?? '',
      text: json['text'] ?? '',
      isUser: json['isUser'] ?? false,
      timestamp: DateTime.parse(json['timestamp']),
      hasAudio: json['hasAudio'] ?? false,
      audioUrl: json['audioUrl'],
      audioData: json['audioData'],
    );
  }

  // V1.5: 转换为JSON用于本地存储
  Map<String, dynamic> toStorage() {
    return {
      'messageId': messageId,
      'text': text,
      'isUser': isUser,
      'timestamp': timestamp.toIso8601String(),
      'hasAudio': hasAudio,
      'audioUrl': audioUrl,
      'audioData': audioData,
    };
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
  final WordService _wordService = WordService();  // V1.5: 单词查询服务
  final SpeechEvalService _speechEvalService = SpeechEvalService();  // V1.6: 语音评分服务

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
    _loadChatHistory();  // V1.5: 加载聊天历史
    _initializeVoiceSession();
  }

  /// 🚀 设置WebSocket回调（模仿py-xiaozhi的即时播放）
  void _setupWebSocketCallbacks() {
    // 收到音频帧立即播放
    _voiceService.onAudioFrameReceived = (String base64Data) {
      // ✅ 精简日志：删除高频音频帧日志
      _streamingPlayer.addAudioFrame(base64Data);

      // 👄 音频帧到达时启动/刷新嘴部同步
      if (_lipSyncController != null) {
        if (!_lipSyncController!.isPlaying) {
          // 第一帧：启动嘴部同步
          _lipSyncController!.startLipSync();
        } else {
          // 后续帧：刷新活动状态（重置不活跃定时器）
          _lipSyncController!.refreshActivity();
        }
      }
    };

    // 收到用户语音识别文字
    _voiceService.onUserTextReceived = (String text) {
      _debugLog('📝 收到用户文字: $text');

      if (_useStreamingPlayback) {
        // V1.6优化: 先立即显示用户消息（不带评分），避免延迟
        final messageId = 'user_${DateTime.now().millisecondsSinceEpoch}';
        final userMessage = ChatMessage(
          messageId: messageId,
          text: text,
          isUser: true,
          timestamp: DateTime.now(),
          speechFeedback: null,  // 初始无评分数据
        );
        _addMessageAndSave(userMessage);  // 立即显示消息

        // V1.6: 异步调用评分API，完成后更新消息
        _evaluateSpeechAsync(messageId, text);
      }
    };

    // 收到AI文本立即显示
    _voiceService.onTextReceived = (String text) {
      _debugLog('📝 收到AI文本: $text');

      // 🚀 只在流式模式下显示（避免与轮询重复）
      if (_useStreamingPlayback) {
        final aiMessage = ChatMessage(
          messageId: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          text: text,
          isUser: false,
          timestamp: DateTime.now(),
          hasAudio: false,  // 音频通过流式播放，不需要关联
        );
        _addMessageAndSave(aiMessage);  // V1.5: 保存聊天历史
        setState(() {
          _isProcessing = false;
        });
        _typingController.stop();
      }
    };

    // 🎭 收到AI表情emoji
    _voiceService.onEmotionReceived = (String emoji) {
      _debugLog('🎭 收到emotion: $emoji');

      // 👄 停止嘴部同步（AI回复结束标志）
      _lipSyncController?.stopLipSync();

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

        // 👄 停止嘴部同步动画（用户开始新的录音）
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

  /// V1.6: 检查文本是否为纯英文
  bool _isEnglishOnly(String text) {
    // 移除标点符号和空格后检查
    final cleanText = text.replaceAll(RegExp(r'[^\w]'), '');
    if (cleanText.isEmpty) return false;

    // 检查是否包含中文字符 (Unicode范围: \u4e00-\u9fff)
    final hasChinese = RegExp(r'[\u4e00-\u9fff]').hasMatch(text);
    if (hasChinese) return false;

    // 检查是否主要由英文字母组成
    final englishLetters = RegExp(r'[a-zA-Z]').allMatches(cleanText).length;
    final ratio = englishLetters / cleanText.length;

    return ratio > 0.7;  // 至少70%是英文字母
  }

  /// V1.6: 异步评分方法 - 评分完成后更新消息
  void _evaluateSpeechAsync(String messageId, String text) async {
    try {
      // V1.6: 语言检测 - 只对纯英文内容评分
      if (!_isEnglishOnly(text)) {
        _debugLog('⏭️ [异步] 检测到中文内容，跳过评分: $text');
        return;
      }

      _debugLog('🎯 [异步] 开始语音评分: $text');
      final speechFeedback = await _speechEvalService.evaluateSpeech(text);
      _debugLog('✅ [异步] 评分完成: ${speechFeedback.overallScore}分');

      // 查找并更新消息
      final messageIndex = _messages.indexWhere((m) => m.messageId == messageId);
      if (messageIndex != -1) {
        setState(() {
          // 创建新的消息对象（包含评分数据）
          _messages[messageIndex] = ChatMessage(
            messageId: messageId,
            text: text,
            isUser: true,
            timestamp: _messages[messageIndex].timestamp,
            speechFeedback: speechFeedback,  // 添加评分数据
          );
        });
        _debugLog('✅ [异步] 消息已更新，评分卡片已显示');
      } else {
        _debugLog('⚠️ [异步] 未找到消息ID: $messageId');
      }
    } catch (e) {
      _debugLog('⚠️ [异步] 评分失败: $e');
      // 评分失败不影响消息显示，用户消息仍然正常显示
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
      print('🔄 [V1.5] 开始初始化语音会话...');

      // 显示加载提示
      setState(() {
        _isProcessing = true;
        _listeningText = "正在初始化语音会话...";
      });

      // 初始化语音会话 (添加15秒超时)
      final result = await _voiceService.initSession(
        autoPlayTts: false,  // 前端播放音频,后端不播放
        saveConversation: true,
        enableEchoCancellation: true,
      ).timeout(
        const Duration(seconds: 15),
        onTimeout: () {
          print('⏱️ [V1.5] 会话初始化超时');
          return {'success': false, 'message': '初始化超时,请检查网络连接'};
        },
      );

      print('📋 [V1.5] 会话初始化结果: $result');

      if (result['success'] == true) {
        print('✅ [V1.5] 会话初始化成功，准备连接WebSocket');

        // 🚀 连接WebSocket接收实时音频推送
        final wsConnected = await _voiceService.connectWebSocket();

        if (wsConnected) {
          print('✅ [V1.5] WebSocket连接成功');

          // ✅ 连接成功后再设置回调，避免被清空
          _setupWebSocketCallbacks();

          setState(() {
            _isSessionInitialized = true;
            _sessionState = result['state'] ?? 'ready';
            _useStreamingPlayback = true;  // 启用流式播放
            _isProcessing = false;
            _listeningText = "";
          });
        } else {
          print('❌ [V1.5] WebSocket连接失败！会话未完全初始化');
          setState(() {
            _isSessionInitialized = false;  // ← 关键修复：标记为未初始化
            _isProcessing = false;
            _listeningText = "";
          });
          _showSnackBar('WebSocket连接失败，请重试');
        }

        // V1.5: 只在聊天历史为空时添加欢迎消息
        if (_messages.isEmpty) {
          _addWelcomeMessage();
        }

        // ❌ 删除旧逻辑: 不再启动状态轮询，完全依赖WebSocket推送
        // _startStatusPolling();
      } else {
        print('❌ [V1.5] 会话初始化失败: ${result['message']}');
        setState(() {
          _isSessionInitialized = false;
          _isProcessing = false;
          _listeningText = "";
        });

        // 显示错误提示
        _showErrorDialog('初始化失败', result['message'] ?? '无法初始化语音会话');
      }
    } catch (e) {
      print('❌ [V1.5] 初始化异常: $e');
      setState(() {
        _isSessionInitialized = false;
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

          final userMessage = ChatMessage(
            messageId: messageId,
            text: userText,
            isUser: true,
            timestamp: DateTime.now(),
          );
          _addMessageAndSave(userMessage);  // V1.5: 保存聊天历史

          // 记录已处理的消息ID
          _lastProcessedMessageId = messageId;

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
    final welcomeMessage = ChatMessage(
      messageId: 'welcome_${DateTime.now().millisecondsSinceEpoch}',
      text: "你好！我是Zoe，你的英语学习伙伴。让我们开始一段有趣的英语对话吧！🎯",
      isUser: false,
      timestamp: DateTime.now(),
      hasAudio: false,
    );
    _addMessageAndSave(welcomeMessage);  // V1.5: 保存聊天历史
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

  /// 取消语音录音
  Future<void> _cancelVoiceRecording() async {
    if (!_isRecording) return;

    try {
      // 调用后端停止录音API(但不处理结果)
      await _voiceService.stopRecording();

      setState(() {
        _isRecording = false;
        _listeningText = "";
      });

      _pulseController.stop();
      _debugLog('❌ 用户取消录音');
    } catch (e) {
      _debugLog('❌ 取消录音失败: $e');
      setState(() {
        _isRecording = false;
      });
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
      final userMessage = ChatMessage(
        messageId: 'user_${DateTime.now().millisecondsSinceEpoch}',
        text: text,
        isUser: true,
        timestamp: DateTime.now(),
      );
      _addMessageAndSave(userMessage);  // V1.5: 保存聊天历史

      setState(() {
        _isProcessing = true;
      });

      _textController.clear();
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

              _addMessageAndSave(aiMessage);  // V1.5: 保存聊天历史

              setState(() {
                _isProcessing = false;
              });

              _typingController.stop();

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
    print('🔄 [V1.5] ChatPage dispose()被调用');

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
    print('🔄 [V1.5] 断开WebSocket连接');
    _voiceService.disconnectWebSocket();
    _streamingPlayer.dispose();

    // V1.5修复: 不在dispose中关闭会话，避免HTTP请求被中断
    // 会话会在后端超时后自动清理，或在下次初始化时复用
    // _voiceService.closeSession();
    print('ℹ️ [V1.5] 保留后端会话以便复用');

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,  // 白色背景
      body: Stack(
        children: [
          // 🎭 Live2D模型背景层（最底层）
          Positioned.fill(
            child: Container(
              color: Colors.white,  // 白色背景
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
                  color: Colors.black87,
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
            child: SizedBox(
              height: 320,
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
      child: Column(  // V1.6: 改为Column，用于显示消息+评分卡片
        crossAxisAlignment: message.isUser
            ? CrossAxisAlignment.end
            : CrossAxisAlignment.start,
        children: [
          Row(
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
                    color: message.isUser ? null : const Color(0xFFF5F5F5),  // AI消息：浅灰色背景
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: Radius.circular(message.isUser ? 16 : 4),
                      bottomRight: Radius.circular(message.isUser ? 4 : 16),
                    ),
                    // 去掉投影
                    boxShadow: message.isUser
                        ? [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.08),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                          ]
                        : null,  // AI消息不显示投影
                  ),
                  // V1.5: 如果是AI消息，使用RichText渲染可点击单词
                  child: message.isUser
                      ? Text(
                          message.text,
                          style: TextStyle(
                            fontSize: 16,  // 从 14 增大到 16
                            color: Colors.white,
                            height: 1.3,
                          ),
                        )
                      : _buildClickableText(message.text),
                ),
              ),
            ],
          ),
          // V1.6: 如果是用户消息且有评分数据，显示评分卡片
          if (message.isUser && message.speechFeedback != null)
            SpeechScoreCard(
              feedback: message.speechFeedback!,
              onGrammarTap: message.speechFeedback!.grammar.hasError
                  ? () => GrammarSuggestionModal.show(
                        context,
                        message.speechFeedback!.grammar,
                      )
                  : null,
              onPronunciationTap: () => PronunciationAnalysisModal.show(
                context,
                message.speechFeedback!.pronunciation,
              ),
              onExpressionTap: () => ExpressionImprovementModal.show(
                context,
                message.speechFeedback!.expression,
                message.speechFeedback!.grammar.original,
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

  // ==================== V1.5: 单词识别与点击功能 ====================

  /// 构建可点击的文本（将英文单词变成可点击的）
  Widget _buildClickableText(String text) {
    // 正则表达式：匹配英文单词（仅字母，长度至少2个字符）
    final wordRegex = RegExp(r'\b[a-zA-Z]{2,}\b');
    final matches = wordRegex.allMatches(text);

    if (matches.isEmpty) {
      // 没有英文单词，直接返回普通Text
      return Text(
        text,
        style: const TextStyle(
          fontSize: 16,  // 从 14 增大到 16
          color: Color(0xFF2D3436),
          height: 1.3,
        ),
      );
    }

    // 构建 TextSpan 列表
    final spans = <TextSpan>[];
    int lastEnd = 0;

    for (final match in matches) {
      // 添加非单词部分（普通文本）
      if (match.start > lastEnd) {
        spans.add(
          TextSpan(
            text: text.substring(lastEnd, match.start),
            style: const TextStyle(
              fontSize: 16,  // 从 14 增大到 16
              color: Color(0xFF2D3436),
              height: 1.3,
            ),
          ),
        );
      }

      // 添加单词部分（可点击，但样式与普通文本一致）
      final word = match.group(0)!;
      spans.add(
        TextSpan(
          text: word,
          style: const TextStyle(
            fontSize: 16,  // 从 14 增大到 16
            color: Color(0xFF2D3436),  // 与普通文本颜色一致
            height: 1.3,
          ),
          recognizer: TapGestureRecognizer()
            ..onTap = () => _onWordTap(word),
        ),
      );

      lastEnd = match.end;
    }

    // 添加最后的非单词部分
    if (lastEnd < text.length) {
      spans.add(
        TextSpan(
          text: text.substring(lastEnd),
          style: const TextStyle(
            fontSize: 16,  // 从 14 增大到 16
            color: Color(0xFF2D3436),
            height: 1.3,
          ),
        ),
      );
    }

    return RichText(
      text: TextSpan(children: spans),
    );
  }

  /// 处理单词点击事件（V1.5.1 - 优化加载体验）
  Future<void> _onWordTap(String word) async {
    print('📖 用户点击单词: $word');

    if (!mounted) return;

    // 显示加载对话框
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 16),
                Text(
                  'AI正在查询单词...',
                  style: TextStyle(fontSize: 16),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    // 查询单词释义（V1.5.1）
    try {
      final result = await _wordService.lookupWord(word);

      if (!mounted) return;

      // 关闭加载对话框
      Navigator.of(context).pop();

      // 显示单词弹窗
      WordPopupSheet.show(context, result);
    } catch (e) {
      if (!mounted) return;

      // 关闭加载对话框
      Navigator.of(context).pop();

      // 显示错误提示
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('查询失败: $e'),
          backgroundColor: Colors.redAccent,
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  // ==================== V1.5: 聊天记录持久化 ====================

  static const String _chatHistoryKey = 'chat_history';
  static const int _maxHistoryMessages = 100;  // 最多保存100条消息

  /// 加载聊天历史
  Future<void> _loadChatHistory() async {
    try {
      print('🔄 [V1.5] 开始加载聊天历史...');
      final prefs = await SharedPreferences.getInstance();
      final historyJson = prefs.getString(_chatHistoryKey);

      if (historyJson != null) {
        final List<dynamic> historyList = jsonDecode(historyJson);
        final loadedMessages = historyList
            .map((json) => ChatMessage.fromStorage(json as Map<String, dynamic>))
            .toList();

        setState(() {
          _messages.clear();
          _messages.addAll(loadedMessages);
        });

        print('✅ [V1.5] 加载聊天历史成功: ${_messages.length} 条消息');

        // 滚动到底部
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _scrollToBottom();
        });
      } else {
        print('ℹ️ [V1.5] 无聊天历史记录');
      }
    } catch (e) {
      print('❌ [V1.5] 加载聊天历史失败: $e');
    }
  }

  /// 保存聊天历史
  Future<void> _saveChatHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // 只保存最近的N条消息
      final messagesToSave = _messages.length > _maxHistoryMessages
          ? _messages.sublist(_messages.length - _maxHistoryMessages)
          : _messages;

      final historyList = messagesToSave.map((msg) => msg.toStorage()).toList();
      final historyJson = jsonEncode(historyList);

      await prefs.setString(_chatHistoryKey, historyJson);
      print('✅ 保存聊天历史: ${messagesToSave.length} 条消息');
    } catch (e) {
      print('❌ 保存聊天历史失败: $e');
    }
  }

  /// 添加消息并保存
  void _addMessageAndSave(ChatMessage message) {
    setState(() {
      _messages.add(message);
    });
    _saveChatHistory();  // 自动保存
    _scrollToBottom();
  }

  Widget _buildInputArea() {
    return Container(
      padding: EdgeInsets.only(
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
          // V1.7: 使用优化的语音输入条组件
          VoiceInputBar(
            isRecording: _isRecording,
            isEnabled: _isSessionInitialized,
            onStartRecording: _startVoiceRecording,
            onStopRecording: _stopVoiceRecording,
            onCancelRecording: _cancelVoiceRecording,
          ),
        ],
      ),
    );
  }
}
