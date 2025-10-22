// 生词本页面 - PocketSpeak V1.5
// 展示用户收藏的生词列表，支持查看释义和删除操作

import 'package:flutter/material.dart';
import '../models/word_definition.dart';
import '../services/word_service.dart';
import '../widgets/word_popup_sheet.dart';

class VocabListPage extends StatefulWidget {
  const VocabListPage({Key? key}) : super(key: key);

  @override
  State<VocabListPage> createState() => _VocabListPageState();
}

class _VocabListPageState extends State<VocabListPage> {
  final WordService _wordService = WordService();

  List<VocabFavorite> _words = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadVocabList();
  }

  /// 加载生词本列表
  Future<void> _loadVocabList() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await _wordService.getFavorites();

      if (mounted) {
        setState(() {
          _words = response.words;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '加载失败: $e';
          _isLoading = false;
        });
      }
    }
  }

  /// 删除单词
  Future<void> _deleteWord(String word) async {
    // 显示确认对话框
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除单词 "$word" 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('删除', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    // 执行删除
    final result = await _wordService.deleteFavorite(word);

    if (!mounted) return;

    if (result['success']) {
      // 删除成功，刷新列表
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? '删除成功'),
          backgroundColor: Colors.green,
        ),
      );
      _loadVocabList();
    } else {
      // 删除失败
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? '删除失败'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
  }

  /// 清空生词本
  Future<void> _clearAll() async {
    if (_words.isEmpty) return;

    // 显示确认对话框
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认清空'),
        content: Text('确定要清空全部 ${_words.length} 个单词吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('清空', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    // 执行清空
    final result = await _wordService.clearFavorites();

    if (!mounted) return;

    if (result['success']) {
      // 清空成功，刷新列表
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? '清空成功'),
          backgroundColor: Colors.green,
        ),
      );
      _loadVocabList();
    } else {
      // 清空失败
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? '清空失败'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
  }

  /// 点击单词，查看完整释义
  Future<void> _viewWordDetail(VocabFavorite vocab) async {
    print('📖 查看单词详情: ${vocab.word}');

    // 显示加载提示
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('正在查询单词...'),
        duration: Duration(seconds: 1),
      ),
    );

    // 重新查询单词完整信息（V1.5.1）
    try {
      final result = await _wordService.lookupWord(vocab.word);

      if (!mounted) return;

      // 显示单词弹窗（标记为已收藏）
      WordPopupSheet.show(
        context,
        result,
        isAlreadyFavorited: true, // 生词本里的单词已经收藏了
      );
    } catch (e) {
      if (!mounted) return;

      // 查询失败，显示简单信息
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('查询失败: $e'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('生词本'),
        backgroundColor: Colors.deepPurple,
        foregroundColor: Colors.white,
        actions: [
          if (_words.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_sweep),
              onPressed: _clearAll,
              tooltip: '清空生词本',
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadVocabList,
              icon: const Icon(Icons.refresh),
              label: const Text('重新加载'),
            ),
          ],
        ),
      );
    }

    if (_words.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.book_outlined,
              size: 80,
              color: Colors.grey.shade300,
            ),
            const SizedBox(height: 16),
            Text(
              '生词本为空',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '在聊天中点击单词收藏到生词本',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade400,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _words.length,
      itemBuilder: (context, index) {
        final vocab = _words[index];
        return _buildVocabCard(vocab);
      },
    );
  }

  Widget _buildVocabCard(VocabFavorite vocab) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: () => _viewWordDetail(vocab),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // 左侧：单词信息
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 单词
                    Text(
                      vocab.word,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.deepPurple,
                      ),
                    ),
                    const SizedBox(height: 4),
                    // 音标
                    if (vocab.phonetic.isNotEmpty)
                      Text(
                        vocab.phonetic,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey.shade600,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    const SizedBox(height: 8),
                    // 释义
                    Text(
                      vocab.definition,
                      style: const TextStyle(
                        fontSize: 14,
                        color: Color(0xFF2D3436),
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 8),
                    // 收藏时间
                    Text(
                      '收藏于 ${vocab.formattedDate}',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade400,
                      ),
                    ),
                  ],
                ),
              ),
              // 右侧：删除按钮
              IconButton(
                icon: const Icon(Icons.delete_outline),
                color: Colors.grey,
                onPressed: () => _deleteWord(vocab.word),
                tooltip: '删除',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
