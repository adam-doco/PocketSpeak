# -*- coding: utf-8 -*-
"""
单词查询路由 - PocketSpeak V1.5
提供单词释义查询和生词本管理接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict

from models.word_models import (
    WordLookupResult,
    WordLookupResultV2,
    WordDefinitionItem,
    VocabFavoriteRequest,
    VocabFavoriteResponse,
    VocabListResponse,
    WordPhonetic
)
from services.word_lookup.youdao_client import YoudaoClient
from services.word_lookup.vocab_storage import vocab_storage_service
from utils.api_config_loader import api_config_loader
from deps.dependencies import get_current_user
from models.user_model import User

# V1.5.1: 引入DeepSeek相关模块
from services.word_lookup.deepseek_word_agent import DeepSeekWordAgent
from services.word_lookup.youdao_audio_agent import YoudaoAudioAgent
from models.word_entry import word_cache


# 创建路由器
router = APIRouter(prefix="/api/words", tags=["words"])


# 初始化有道客户端
def get_youdao_client() -> YoudaoClient:
    """获取有道API客户端"""
    config = api_config_loader.get_youdao_config()

    if not config.get('enabled', False):
        raise HTTPException(status_code=503, detail="词典服务未启用")

    return YoudaoClient(
        app_id=config['app_id'],
        app_key=config['app_key'],
        base_url=config['base_url'],
        timeout=config.get('timeout', 10)
    )


@router.get("/lookup", response_model=WordLookupResultV2)
async def lookup_word(word: str):
    """
    查询单词释义（V1.5.1：使用DeepSeek AI，符合PRD要求）

    Args:
        word: 要查询的英文单词

    Returns:
        WordLookupResultV2: 单词释义结果（PRD V1.5.1格式）

    Raises:
        HTTPException: 503 - 词典服务未启用
        HTTPException: 400 - 查询失败
    """
    if not word or not word.strip():
        raise HTTPException(status_code=400, detail="单词不能为空")

    word = word.strip().lower()

    print(f"\n📖 收到单词查询请求（V1.5.1）: {word}")

    try:
        # V1.5.1: 检查缓存
        if word_cache.exists(word):
            cached_result = word_cache.get(word)
            print(f"✅ 从缓存返回: {word}")
            # 返回V1.5.1格式
            return WordLookupResultV2(
                word=cached_result.word,
                uk_phonetic=cached_result.uk_phonetic,
                us_phonetic=cached_result.us_phonetic,
                uk_audio_url=cached_result.uk_audio_url,
                us_audio_url=cached_result.us_audio_url,
                definitions=[WordDefinitionItem(pos=d.pos, meaning=d.meaning) for d in cached_result.definitions],
                mnemonic=cached_result.mnemonic,
                source=cached_result.source,
                created_at=cached_result.created_at.isoformat()
            )

        # V1.5.1: 使用DeepSeek查询
        config = api_config_loader.get_config()['deepseek']
        if not config.get('enabled', False):
            raise HTTPException(status_code=503, detail="DeepSeek服务未启用")

        deepseek_agent = DeepSeekWordAgent(
            api_key=config['api_key'],
            base_url=config['base_url'],
            model=config.get('model', 'deepseek-chat'),
            timeout=config.get('timeout', 30),
            max_tokens=config.get('max_tokens', 500)
        )

        ai_result = await deepseek_agent.lookup_word(word)

        if not ai_result['success']:
            raise HTTPException(
                status_code=400,
                detail=ai_result.get('error', 'AI查询失败')
            )

        # 生成音频URL
        audio_agent = YoudaoAudioAgent(
            app_id=api_config_loader.get_youdao_config()['app_id'],
            app_key=api_config_loader.get_youdao_config()['app_key']
        )
        audio_result = await audio_agent.get_phonetics_and_audio(word)

        # 缓存到V1.5.1缓存系统
        from models.word_entry import WordEntryResponse, WordDefinition
        from datetime import datetime

        cache_entry = WordEntryResponse(
            word=ai_result['word'],
            uk_phonetic=ai_result['uk_phonetic'],
            us_phonetic=ai_result['us_phonetic'],
            uk_audio_url=audio_result['uk_audio_url'],
            us_audio_url=audio_result['us_audio_url'],
            definitions=[WordDefinition(**d) for d in ai_result['definitions']],
            mnemonic=ai_result['mnemonic'],
            source="AI + 有道API",
            created_at=datetime.now()
        )
        word_cache.set(word, cache_entry)

        # 返回V1.5.1格式（符合PRD）
        return WordLookupResultV2(
            word=ai_result['word'],
            uk_phonetic=ai_result['uk_phonetic'],
            us_phonetic=ai_result['us_phonetic'],
            uk_audio_url=audio_result['uk_audio_url'],
            us_audio_url=audio_result['us_audio_url'],
            definitions=[WordDefinitionItem(**d) for d in ai_result['definitions']],
            mnemonic=ai_result['mnemonic'],
            source="AI + 有道API",
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查询单词异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/favorite", response_model=VocabFavoriteResponse)
async def favorite_word(
    request: VocabFavoriteRequest,
    current_user: User = Depends(get_current_user)
):
    """
    收藏单词到生词本

    需要认证：Bearer Token

    Args:
        request: 收藏请求
        current_user: 当前登录用户

    Returns:
        VocabFavoriteResponse: 收藏结果

    Raises:
        HTTPException: 401 - 未认证
        HTTPException: 400 - 收藏失败
    """
    print(f"\n⭐ 收到收藏单词请求: {request.word} (用户: {current_user.email})")

    try:
        result = vocab_storage_service.add_word(
            user_id=current_user.user_id,
            word=request.word,
            definition=request.definition,
            phonetic=request.phonetic
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return VocabFavoriteResponse(
            success=True,
            message=result['message']
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 收藏单词异常: {e}")
        raise HTTPException(status_code=500, detail=f"收藏失败: {str(e)}")


@router.get("/favorites", response_model=VocabListResponse)
async def get_favorites(current_user: User = Depends(get_current_user)):
    """
    获取生词本列表

    需要认证：Bearer Token

    Args:
        current_user: 当前登录用户

    Returns:
        VocabListResponse: 生词列表

    Raises:
        HTTPException: 401 - 未认证
    """
    print(f"\n📚 获取生词本: 用户 {current_user.email}")

    try:
        words = vocab_storage_service.get_words(current_user.user_id)

        return VocabListResponse(
            success=True,
            words=words,
            total=len(words)
        )

    except Exception as e:
        print(f"❌ 获取生词本异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.delete("/favorite/{word}")
async def delete_favorite(
    word: str,
    current_user: User = Depends(get_current_user)
):
    """
    删除生词

    需要认证：Bearer Token

    Args:
        word: 要删除的单词
        current_user: 当前登录用户

    Returns:
        Dict: 删除结果

    Raises:
        HTTPException: 401 - 未认证
        HTTPException: 400 - 删除失败
    """
    print(f"\n🗑️ 删除生词: {word} (用户: {current_user.email})")

    try:
        result = vocab_storage_service.delete_word(current_user.user_id, word)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 删除生词异常: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/favorites/clear")
async def clear_favorites(current_user: User = Depends(get_current_user)):
    """
    清空生词本

    需要认证：Bearer Token

    Args:
        current_user: 当前登录用户

    Returns:
        Dict: 清空结果

    Raises:
        HTTPException: 401 - 未认证
    """
    print(f"\n🗑️ 清空生词本: 用户 {current_user.email}")

    try:
        result = vocab_storage_service.clear_words(current_user.user_id)

        return result

    except Exception as e:
        print(f"❌ 清空生词本异常: {e}")
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")
