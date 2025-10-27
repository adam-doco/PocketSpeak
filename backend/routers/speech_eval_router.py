# -*- coding: utf-8 -*-
"""
语音评分API路由 - PocketSpeak V1.7
提供语音评分接口（使用豆包AI - 性能优化版）
"""

from fastapi import APIRouter, HTTPException, Body
from models.speech_eval_models import SpeechFeedbackRequest, SpeechFeedbackResponse
from services.speech_eval.eval_service import SpeechEvaluationService
from utils.api_config_loader import api_config_loader

# 创建路由器
router = APIRouter(prefix="/api/eval", tags=["语音评分"])

# 加载豆包评分专用配置（V1.7: 使用豆包AI提升性能）
config = api_config_loader.get_config()
doubao_eval_config = config.get('doubao_eval', {})

if not doubao_eval_config.get('enabled'):
    print("⚠️ 豆包评分配置未启用，语音评分功能将不可用")

# 初始化评分服务
eval_service = None
if doubao_eval_config.get('enabled'):
    eval_service = SpeechEvaluationService(doubao_eval_config)
    print("✅ 语音评分服务已启用（使用豆包AI）")


@router.post("/speech-feedback", response_model=SpeechFeedbackResponse)
async def evaluate_speech(
    request: SpeechFeedbackRequest = Body(
        ...,
        example={
            "transcript": "I like to watch movie in my free time"
        }
    )
):
    """
    评估用户语音表达

    对用户的语音文本进行三维度评分：
    - 语法准确性
    - 发音评分
    - 表达地道程度

    Args:
        request: 评分请求，包含语音识别文本

    Returns:
        SpeechFeedbackResponse: 完整的评分结果

    Raises:
        HTTPException: 评分失败时返回错误
    """
    try:
        # 检查服务是否可用
        if not eval_service:
            raise HTTPException(
                status_code=503,
                detail="语音评分服务未启用，请检查豆包配置"
            )

        # 验证输入
        if not request.transcript or len(request.transcript.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="transcript不能为空"
            )

        print(f"\n🎯 收到评分请求: {request.transcript}")

        # 执行评分
        result = await eval_service.evaluate(request.transcript)

        print(f"✅ 评分成功返回: {result.overall_score}分")

        return result

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"❌ 评分接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"评分失败: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        Dict: 服务状态
    """
    return {
        "status": "healthy" if eval_service else "unavailable",
        "service": "speech-evaluation",
        "version": "1.6"
    }
