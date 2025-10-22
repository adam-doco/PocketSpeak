# -*- coding: utf-8 -*-
"""
单词查询路由（V1.5.1） - PocketSpeak
提供AI驱动的单词查询功能
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from models.word_entry import WordEntryResponse, WordDefinition, word_cache
from services.word_lookup.deepseek_word_agent import DeepSeekWordAgent
from services.word_lookup.youdao_audio_agent import YoudaoAudioAgent
from utils.api_config_loader import api_config_loader


# 创建路由器
router = APIRouter(prefix="/api/word", tags=["word-lookup-v2"])


# 初始化Agent
def get_deepseek_agent() -> DeepSeekWordAgent:
    """获取DeepSeek Agent实例"""
    config = api_config_loader.get_config()['deepseek']

    if not config.get('enabled', False):
        raise HTTPException(status_code=503, detail="DeepSeek服务未启用")

    return DeepSeekWordAgent(
        api_key=config['api_key'],
        base_url=config['base_url'],
        model=config.get('model', 'deepseek-chat'),
        timeout=config.get('timeout', 30),
        max_tokens=config.get('max_tokens', 500)
    )


def get_youdao_audio_agent() -> YoudaoAudioAgent:
    """获取有道音频Agent实例"""
    config = api_config_loader.get_youdao_config()

    return YoudaoAudioAgent(
        app_id=config['app_id'],
        app_key=config['app_key']
    )


@router.get("/lookup", response_model=WordEntryResponse)
async def lookup_word(word: str):
    """
    查询单词释义（V1.5.1版本）

    流程：
    1. 检查缓存
    2. 调用DeepSeek获取释义和联想记忆
    3. 调用有道TTS获取音频URL
    4. 合并结果并缓存
    5. 返回前端

    Args:
        word: 要查询的英文单词

    Returns:
        WordEntryResponse: 单词完整数据

    Raises:
        HTTPException: 503 - 服务未启用
        HTTPException: 400 - 查询失败
    """
    if not word or not word.strip():
        raise HTTPException(status_code=400, detail="单词不能为空")

    word = word.strip().lower()

    print(f"\n📖 收到单词查询请求（V1.5.1）: {word}")

    try:
        # 1. 检查缓存
        if word_cache.exists(word):
            cached_result = word_cache.get(word)
            print(f"✅ 从缓存返回: {word}")
            return cached_result

        # 2. 调用DeepSeek Agent
        deepseek_agent = get_deepseek_agent()
        ai_result = await deepseek_agent.lookup_word(word)

        if not ai_result['success']:
            raise HTTPException(
                status_code=400,
                detail=ai_result.get('error', 'AI查询失败')
            )

        # 3. 调用有道音频Agent
        audio_agent = get_youdao_audio_agent()
        audio_result = await audio_agent.get_phonetics_and_audio(word)

        # 4. 合并结果
        result = WordEntryResponse(
            word=ai_result['word'],
            uk_phonetic=ai_result['uk_phonetic'],  # ✅ 使用DeepSeek返回的音标
            us_phonetic=ai_result['us_phonetic'],  # ✅ 使用DeepSeek返回的音标
            uk_audio_url=audio_result['uk_audio_url'],
            us_audio_url=audio_result['us_audio_url'],
            definitions=[WordDefinition(**d) for d in ai_result['definitions']],
            mnemonic=ai_result['mnemonic'],
            source="AI + 有道API",
            created_at=datetime.now()
        )

        # 5. 缓存结果
        word_cache.set(word, result)

        print(f"✅ 查询完成: {word}, {len(result.definitions)}条释义")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查询单词异常: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    return {
        "cache_size": word_cache.size(),
        "max_size": word_cache.max_size
    }


@router.delete("/cache/clear")
async def clear_cache():
    """清空缓存"""
    word_cache.clear()
    return {"success": True, "message": "缓存已清空"}
