# -*- coding: utf-8 -*-
"""
语音评分数据模型 - PocketSpeak V1.6
定义语音评分系统的Pydantic数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class WordPronunciation(BaseModel):
    """单词发音评分模型"""
    word: str = Field(..., description="单词")
    status: str = Field(..., description="发音状态: good, bad, needs_improvement")


class PronunciationDetail(BaseModel):
    """发音详细评分模型"""
    score: int = Field(..., ge=0, le=100, description="发音总分 (0-100)")
    words: List[WordPronunciation] = Field(..., description="逐词发音评分")
    fluency: int = Field(..., ge=0, le=100, description="流利度 (0-100)")
    clarity: int = Field(..., ge=0, le=100, description="清晰度 (0-100)")
    completeness: int = Field(..., ge=0, le=100, description="完整度 (0-100)")
    speed_wpm: int = Field(..., gt=0, description="语速 (词/分钟)")


class GrammarAnalysis(BaseModel):
    """语法分析模型"""
    has_error: bool = Field(..., description="是否有语法错误")
    original: str = Field(..., description="原始句子")
    suggestion: Optional[str] = Field(None, description="修改建议")
    reason: Optional[str] = Field(None, description="错误原因说明")


class ExpressionEvaluation(BaseModel):
    """表达地道程度评估模型"""
    level: str = Field(..., description="地道程度: 不地道, 一般, 地道, 非常地道")
    suggestion: Optional[str] = Field(None, description="优化建议表达")
    reason: Optional[str] = Field(None, description="优化原因说明")


class SpeechFeedbackResponse(BaseModel):
    """语音评分完整响应模型"""
    overall_score: int = Field(..., ge=0, le=100, description="综合得分 (0-100)")
    grammar: GrammarAnalysis = Field(..., description="语法分析")
    pronunciation: PronunciationDetail = Field(..., description="发音评分详情")
    expression: ExpressionEvaluation = Field(..., description="表达地道程度")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="评分时间")


class SpeechFeedbackRequest(BaseModel):
    """语音评分请求模型"""
    transcript: str = Field(..., description="语音识别文本")
    # 注意: 实际音频文件通过 FastAPI 的 UploadFile 处理，不在这里定义
