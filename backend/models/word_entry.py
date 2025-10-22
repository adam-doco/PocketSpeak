# -*- coding: utf-8 -*-
"""
单词条目数据模型 - PocketSpeak V1.5.1
用于缓存查询过的单词
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class WordDefinition(BaseModel):
    """单词释义模型"""
    pos: str  # 词性（如：名词、动词、形容词等）
    meaning: str  # 中文释义


class WordEntryResponse(BaseModel):
    """单词查询响应模型"""
    word: str
    uk_phonetic: str
    us_phonetic: str
    uk_audio_url: str
    us_audio_url: str
    definitions: List[WordDefinition]
    mnemonic: str
    source: str = "AI + 有道API"
    created_at: datetime


# V1.5.1: 简化版缓存模型（使用内存缓存，不使用数据库）
class WordCache:
    """单词缓存管理器（内存版）"""

    def __init__(self, max_size: int = 200):
        """
        初始化缓存管理器

        Args:
            max_size: 最大缓存单词数
        """
        self._cache: dict[str, WordEntryResponse] = {}
        self.max_size = max_size

    def get(self, word: str) -> Optional[WordEntryResponse]:
        """
        从缓存获取单词

        Args:
            word: 单词

        Returns:
            Optional[WordEntryResponse]: 缓存的单词数据，不存在返回None
        """
        key = word.lower().strip()
        return self._cache.get(key)

    def set(self, word: str, data: WordEntryResponse):
        """
        设置缓存

        Args:
            word: 单词
            data: 单词数据
        """
        key = word.lower().strip()

        # 如果缓存已满，删除最早的条目（FIFO）
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key)
            print(f"🗑️ 缓存已满，删除: {oldest_key}")

        self._cache[key] = data
        print(f"💾 缓存单词: {key} (总数: {len(self._cache)})")

    def exists(self, word: str) -> bool:
        """
        检查单词是否在缓存中

        Args:
            word: 单词

        Returns:
            bool: 是否存在
        """
        key = word.lower().strip()
        return key in self._cache

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        print("🗑️ 缓存已清空")

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


# 全局缓存实例
word_cache = WordCache()
