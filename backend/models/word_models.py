# -*- coding: utf-8 -*-
"""
单词查询相关数据模型 - PocketSpeak V1.5.1
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class WordPhonetic(BaseModel):
    """单词音标模型（V1.5：支持音频URL）"""
    us: str = ""  # 美式音标
    uk: str = ""  # 英式音标
    us_audio: str = ""  # V1.5: 美式发音音频URL
    uk_audio: str = ""  # V1.5: 英式发音音频URL


class WordDefinitionItem(BaseModel):
    """单词释义项（V1.5.1新增）"""
    pos: str  # 词性（如：形容词、名词、动词等）
    meaning: str  # 中文释义


class WordLookupResultV2(BaseModel):
    """单词查询结果模型（V1.5.1：符合PRD要求）"""
    word: str
    uk_phonetic: str
    us_phonetic: str
    uk_audio_url: str
    us_audio_url: str
    definitions: List[WordDefinitionItem]
    mnemonic: str  # 联想记忆
    source: str = "AI + 有道API"
    created_at: str  # ISO格式时间字符串


class WordLookupResult(BaseModel):
    """单词查询结果模型（旧版，向后兼容）"""
    success: bool
    word: str = ""
    phonetic: Optional[WordPhonetic] = None
    definitions: List[str] = []
    error: Optional[str] = None


class VocabFavorite(BaseModel):
    """生词收藏模型"""
    word: str
    definition: str  # 主要释义（中文）
    phonetic: str    # 音标（美式优先）
    created_at: str  # ISO格式时间字符串


class VocabFavoriteRequest(BaseModel):
    """收藏单词请求模型"""
    word: str
    definition: str
    phonetic: str

    class Config:
        json_schema_extra = {
            "example": {
                "word": "hello",
                "definition": "你好",
                "phonetic": "/həˈloʊ/"
            }
        }


class VocabFavoriteResponse(BaseModel):
    """收藏单词响应模型"""
    success: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "收藏成功"
            }
        }


class VocabListResponse(BaseModel):
    """生词列表响应模型"""
    success: bool
    words: List[VocabFavorite]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total": 2,
                "words": [
                    {
                        "word": "hello",
                        "definition": "你好",
                        "phonetic": "/həˈloʊ/",
                        "created_at": "2025-01-20T10:30:00"
                    }
                ]
            }
        }
