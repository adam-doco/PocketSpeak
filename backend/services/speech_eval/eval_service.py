# -*- coding: utf-8 -*-
"""
语音评分核心服务 - PocketSpeak V1.6
整合DeepSeek评分，提供完整的评分服务
"""

from typing import Dict
from .deepseek_client import DeepSeekSpeechEvalClient
from models.speech_eval_models import (
    SpeechFeedbackResponse,
    GrammarAnalysis,
    PronunciationDetail,
    ExpressionEvaluation,
    WordPronunciation
)


class SpeechEvaluationService:
    """语音评分服务"""

    def __init__(self, deepseek_config: Dict):
        """
        初始化评分服务

        Args:
            deepseek_config: DeepSeek配置字典
        """
        self.deepseek_client = DeepSeekSpeechEvalClient(
            api_key=deepseek_config['api_key'],
            base_url=deepseek_config['base_url'],
            model=deepseek_config.get('model', 'deepseek-chat'),
            timeout=deepseek_config.get('timeout', 30)
        )

        print("✅ 语音评分服务初始化完成")

    async def evaluate(self, transcript: str) -> SpeechFeedbackResponse:
        """
        评估用户语音

        Args:
            transcript: 语音识别文本

        Returns:
            SpeechFeedbackResponse: 评分响应

        Raises:
            Exception: 评分失败时抛出异常
        """
        print(f"\n📝 开始评分: {transcript}")

        # 调用DeepSeek进行评分
        result = await self.deepseek_client.evaluate_speech(transcript)

        if not result.get('success'):
            error_msg = result.get('error', '评分失败')
            print(f"❌ 评分失败: {error_msg}")
            raise Exception(error_msg)

        # 转换为Pydantic模型
        try:
            # 构造语法分析
            grammar_data = result['grammar']
            grammar = GrammarAnalysis(
                has_error=grammar_data['has_error'],
                original=grammar_data['original'],
                suggestion=grammar_data.get('suggestion'),
                reason=grammar_data.get('reason')
            )

            # 构造发音评分
            pronunciation_data = result['pronunciation']
            words = [
                WordPronunciation(word=w['word'], status=w['status'])
                for w in pronunciation_data['words']
            ]
            pronunciation = PronunciationDetail(
                score=pronunciation_data['score'],
                words=words,
                fluency=pronunciation_data['fluency'],
                clarity=pronunciation_data['clarity'],
                completeness=pronunciation_data['completeness'],
                speed_wpm=pronunciation_data['speed_wpm']
            )

            # 构造表达评估
            expression_data = result['expression']
            expression = ExpressionEvaluation(
                level=expression_data['level'],
                suggestion=expression_data.get('suggestion'),
                reason=expression_data.get('reason')
            )

            # 构造完整响应
            response = SpeechFeedbackResponse(
                overall_score=result['overall_score'],
                grammar=grammar,
                pronunciation=pronunciation,
                expression=expression
            )

            print(f"✅ 评分完成: 综合得分 {response.overall_score}")
            return response

        except Exception as e:
            print(f"❌ 数据转换失败: {e}")
            raise Exception(f"评分数据格式错误: {str(e)}")
