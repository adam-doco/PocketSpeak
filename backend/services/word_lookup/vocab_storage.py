# -*- coding: utf-8 -*-
"""
生词本存储服务 - PocketSpeak V1.5
管理用户收藏的生词
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from models.word_models import VocabFavorite


class VocabStorageService:
    """生词本存储服务"""

    def __init__(self):
        """初始化存储服务"""
        # 数据文件路径
        backend_dir = Path(__file__).parent.parent.parent
        self.data_dir = backend_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.vocab_file = self.data_dir / "vocab_favorites.json"

        # 确保文件存在
        self._ensure_file()

    def _ensure_file(self):
        """确保数据文件存在"""
        if not self.vocab_file.exists():
            self.vocab_file.write_text(
                json.dumps({}, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            print(f"✅ 创建生词本数据文件: {self.vocab_file}")

    def _load_data(self) -> Dict:
        """加载生词本数据"""
        try:
            return json.loads(self.vocab_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"❌ 加载生词本数据失败: {e}")
            return {}

    def _save_data(self, data: Dict) -> bool:
        """保存生词本数据"""
        try:
            self.vocab_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"❌ 保存生词本数据失败: {e}")
            return False

    def add_word(self, user_id: str, word: str, definition: str, phonetic: str) -> Dict:
        """
        添加生词到收藏

        Args:
            user_id: 用户ID
            word: 单词
            definition: 释义（中文）
            phonetic: 音标

        Returns:
            Dict: 操作结果
        """
        try:
            data = self._load_data()

            # 初始化用户词库
            if user_id not in data:
                data[user_id] = {"words": []}

            # 检查是否已收藏
            existing_words = [w['word'].lower() for w in data[user_id]['words']]
            if word.lower() in existing_words:
                return {
                    'success': False,
                    'message': '该单词已在生词本中'
                }

            # 添加新单词
            vocab = {
                'word': word,
                'definition': definition,
                'phonetic': phonetic,
                'created_at': datetime.now().isoformat()
            }

            data[user_id]['words'].insert(0, vocab)  # 新词在最前面

            # 保存数据
            if self._save_data(data):
                print(f"✅ 用户 {user_id} 收藏单词: {word}")
                return {
                    'success': True,
                    'message': '收藏成功'
                }
            else:
                return {
                    'success': False,
                    'message': '保存失败'
                }

        except Exception as e:
            print(f"❌ 添加生词异常: {e}")
            return {
                'success': False,
                'message': f'添加失败: {str(e)}'
            }

    def get_words(self, user_id: str) -> List[VocabFavorite]:
        """
        获取用户的生词列表

        Args:
            user_id: 用户ID

        Returns:
            List[VocabFavorite]: 生词列表
        """
        try:
            data = self._load_data()

            if user_id not in data:
                return []

            words_data = data[user_id].get('words', [])

            # 转换为模型对象
            words = []
            for word_data in words_data:
                try:
                    words.append(VocabFavorite(**word_data))
                except Exception as e:
                    print(f"⚠️ 解析生词数据失败: {e}")
                    continue

            return words

        except Exception as e:
            print(f"❌ 获取生词列表异常: {e}")
            return []

    def delete_word(self, user_id: str, word: str) -> Dict:
        """
        删除生词

        Args:
            user_id: 用户ID
            word: 要删除的单词

        Returns:
            Dict: 操作结果
        """
        try:
            data = self._load_data()

            if user_id not in data:
                return {
                    'success': False,
                    'message': '用户没有生词本'
                }

            # 查找并删除单词
            words = data[user_id]['words']
            original_count = len(words)

            data[user_id]['words'] = [
                w for w in words
                if w['word'].lower() != word.lower()
            ]

            if len(data[user_id]['words']) == original_count:
                return {
                    'success': False,
                    'message': '该单词不在生词本中'
                }

            # 保存数据
            if self._save_data(data):
                print(f"✅ 用户 {user_id} 删除单词: {word}")
                return {
                    'success': True,
                    'message': '删除成功'
                }
            else:
                return {
                    'success': False,
                    'message': '保存失败'
                }

        except Exception as e:
            print(f"❌ 删除生词异常: {e}")
            return {
                'success': False,
                'message': f'删除失败: {str(e)}'
            }

    def clear_words(self, user_id: str) -> Dict:
        """
        清空用户的生词本

        Args:
            user_id: 用户ID

        Returns:
            Dict: 操作结果
        """
        try:
            data = self._load_data()

            if user_id in data:
                data[user_id]['words'] = []

            if self._save_data(data):
                print(f"✅ 用户 {user_id} 清空生词本")
                return {
                    'success': True,
                    'message': '清空成功'
                }
            else:
                return {
                    'success': False,
                    'message': '保存失败'
                }

        except Exception as e:
            print(f"❌ 清空生词本异常: {e}")
            return {
                'success': False,
                'message': f'清空失败: {str(e)}'
            }


# 创建全局单例
vocab_storage_service = VocabStorageService()
