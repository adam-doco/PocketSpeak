// 单词释义弹窗组件 - PocketSpeak V1.5
// 底部弹窗显示单词释义、音标、发音按钮和收藏功能

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import '../models/word_definition.dart';
import '../services/word_service.dart';

class WordPopupSheet extends StatefulWidget {
  final WordLookupResult lookupResult;
  final bool isAlreadyFavorited; // 是否已在生词本中

  const WordPopupSheet({
    Key? key,
    required this.lookupResult,
    this.isAlreadyFavorited = false, // 默认未收藏
  }) : super(key: key);

  /// 显示单词弹窗（静态方法）
  static void show(
    BuildContext context,
    WordLookupResult result, {
    bool isAlreadyFavorited = false,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => WordPopupSheet(
        lookupResult: result,
        isAlreadyFavorited: isAlreadyFavorited,
      ),
    );
  }

  @override
  State<WordPopupSheet> createState() => _WordPopupSheetState();
}

class _WordPopupSheetState extends State<WordPopupSheet> {
  final WordService _wordService = WordService();
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isFavoriting = false;
  late bool _isFavorited; // 是否已收藏
  bool _isPlayingUs = false;
  bool _isPlayingUk = false;

  @override
  void initState() {
    super.initState();
    // 根据传入的参数初始化收藏状态
    _isFavorited = widget.isAlreadyFavorited;
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  /// 收藏单词到生词本
  Future<void> _favoriteWord() async {
    if (_isFavoriting || _isFavorited) return; // 已收藏则不再执行

    setState(() {
      _isFavoriting = true;
    });

    final result = widget.lookupResult;

    final response = await _wordService.favoriteWord(
      word: result.word,
      definition: result.mainDefinition,
      phonetic: result.mainPhonetic,
    );

    if (!mounted) return;

    setState(() {
      _isFavoriting = false;
      // 收藏成功后,标记为已收藏
      if (response['success']) {
        _isFavorited = true;
      }
    });

    // 显示提示消息
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response['message'] ?? '操作完成'),
        backgroundColor:
            response['success'] ? Colors.green : Colors.orangeAccent,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.lookupResult;

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 顶部：单词 + 关闭按钮
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // 单词本体
                  Expanded(
                    child: Text(
                      result.word,
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  // 关闭按钮
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),

              const SizedBox(height: 16),

              // 音标区域（V1.5.1）
              _buildPhoneticRow(
                label: '美式',
                phonetic: result.usPhonetic,
                isPlaying: _isPlayingUs,
                onPlay: result.usPhonetic.isNotEmpty
                    ? () => _playPronunciation('us')
                    : null,
              ),
              const SizedBox(height: 8),
              _buildPhoneticRow(
                label: '英式',
                phonetic: result.ukPhonetic,
                isPlaying: _isPlayingUk,
                onPlay: result.ukPhonetic.isNotEmpty
                    ? () => _playPronunciation('uk')
                    : null,
              ),
              const SizedBox(height: 20),

              // 释义标题
              const Text(
                '释义',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey,
                ),
              ),

              const SizedBox(height: 12),

              // 释义列表（V1.5.1：显示词性+释义）
              if (result.definitions.isNotEmpty)
                ...result.definitions.map(
                      (def) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // 词性标签
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.deepPurple.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                def.pos,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Colors.deepPurple,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            // 释义
                            Expanded(
                              child: Text(
                                def.meaning,
                                style: const TextStyle(
                                  fontSize: 15,
                                  height: 1.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
              else
                const Text(
                  '暂无释义',
                  style: TextStyle(
                    fontSize: 15,
                    color: Colors.grey,
                  ),
                ),

              const SizedBox(height: 20),

              // 联想记忆（V1.5.1新增）
              if (result.mnemonic.isNotEmpty) ...[
                const Text(
                  '联想记忆',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.amber.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Colors.amber.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.lightbulb_outline,
                        color: Colors.amber,
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          result.mnemonic,
                          style: const TextStyle(
                            fontSize: 14,
                            height: 1.6,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],

              // 收藏按钮
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: (_isFavoriting || _isFavorited) ? null : _favoriteWord,
                  icon: _isFavoriting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Icon(_isFavorited ? Icons.check : Icons.star_border),
                  label: Text(
                    _isFavoriting
                        ? '收藏中...'
                        : _isFavorited
                            ? '已加入生词本'
                            : '加入生词本',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isFavorited ? Colors.grey : Colors.deepPurple,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建音标行
  Widget _buildPhoneticRow({
    required String label,
    required String phonetic,
    bool isPlaying = false,
    VoidCallback? onPlay,
  }) {
    return Row(
      children: [
        // 标签（美式/英式）
        Container(
          width: 40,
          alignment: Alignment.centerLeft,
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
        ),
        const SizedBox(width: 8),
        // 音标
        Expanded(
          child: Text(
            phonetic.isNotEmpty ? phonetic : '暂无',
            style: const TextStyle(
              fontSize: 16,
              fontStyle: FontStyle.italic,
            ),
          ),
        ),
        // 播放按钮
        if (onPlay != null)
          IconButton(
            icon: isPlaying
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.deepPurple,
                    ),
                  )
                : const Icon(Icons.volume_up, size: 24),
            onPressed: isPlaying ? null : onPlay,
            tooltip: '播放发音',
            color: Colors.deepPurple,
          )
        else
          const SizedBox(width: 48), // 占位，保持对齐
      ],
    );
  }

  /// 播放发音（V1.5.1）
  Future<void> _playPronunciation(String type) async {
    final result = widget.lookupResult;
    final audioUrl = type == 'us' ? result.usAudioUrl : result.ukAudioUrl;

    if (audioUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('暂无${type == "us" ? "美式" : "英式"}发音'),
          duration: const Duration(seconds: 1),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    try {
      // 设置播放状态
      setState(() {
        if (type == 'us') {
          _isPlayingUs = true;
        } else {
          _isPlayingUk = true;
        }
      });

      print('🔊 播放${type == "us" ? "美式" : "英式"}发音: ${widget.lookupResult.word}');

      // V1.5: 将相对路径转换为完整URL
      // iOS真机测试：使用 WordService.baseUrl 而非硬编码 localhost
      final fullAudioUrl = audioUrl.startsWith('http')
          ? audioUrl
          : '${WordService.baseUrl}$audioUrl';

      print('🔗 音频URL: $fullAudioUrl');

      // 播放音频
      await _audioPlayer.setUrl(fullAudioUrl);

      // 设置音量（增大到1.5，放大50%）
      // just_audio支持大于1.0的音量值来放大音频
      await _audioPlayer.setVolume(1.5);

      await _audioPlayer.play();

      // 等待播放完成
      await _audioPlayer.playerStateStream.firstWhere(
        (state) => state.processingState == ProcessingState.completed,
      );
    } catch (e) {
      print('❌ 播放发音失败: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('播放失败: ${e.toString()}'),
            duration: const Duration(seconds: 2),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // 重置播放状态
      if (mounted) {
        setState(() {
          if (type == 'us') {
            _isPlayingUs = false;
          } else {
            _isPlayingUk = false;
          }
        });
      }
    }
  }
}
