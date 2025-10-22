# -*- coding: utf-8 -*-
"""
音频代理路由 - PocketSpeak V1.5
代理并缓存外部音频资源，解决外部API不稳定问题
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import httpx
import hashlib
from pathlib import Path
from typing import Optional, Literal

from services.word_lookup.youdao_tts_client import YoudaoTTSClient
from utils.api_config_loader import api_config_loader

router = APIRouter(prefix="/api/audio", tags=["audio"])

# 音频缓存目录
AUDIO_CACHE_DIR = Path("data/audio_cache")
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_tts_client() -> YoudaoTTSClient:
    """获取有道TTS客户端"""
    config = api_config_loader.get_youdao_config()
    return YoudaoTTSClient(
        app_id=config['app_id'],
        app_key=config['app_key'],
        timeout=config.get('timeout', 10)
    )


def get_cache_path(url: str) -> Path:
    """根据URL生成缓存文件路径"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return AUDIO_CACHE_DIR / f"{url_hash}.mp3"


@router.get("/proxy")
async def proxy_audio(url: str):
    """
    代理外部音频资源

    Args:
        url: 音频URL

    Returns:
        音频文件流

    Raises:
        HTTPException: 400 - URL无效
        HTTPException: 404 - 音频获取失败
    """
    if not url or not url.startswith('http'):
        raise HTTPException(status_code=400, detail="无效的音频URL")

    # 检查缓存
    cache_path = get_cache_path(url)
    if cache_path.exists():
        print(f"🎵 从缓存返回音频: {cache_path.name}")
        return Response(
            content=cache_path.read_bytes(),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",  # 缓存1天
                "Access-Control-Allow-Origin": "*"
            }
        )

    # 下载音频
    try:
        print(f"⬇️ 下载音频: {url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"音频下载失败: HTTP {response.status_code}"
                )

            audio_data = response.content

            # 保存到缓存
            cache_path.write_bytes(audio_data)
            print(f"💾 音频已缓存: {cache_path.name} ({len(audio_data)} bytes)")

            return Response(
                content=audio_data,
                media_type="audio/mpeg",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )

    except httpx.TimeoutException:
        print(f"⏱️ 音频下载超时: {url}")
        raise HTTPException(status_code=504, detail="音频下载超时")
    except Exception as e:
        print(f"❌ 音频代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"音频获取失败: {str(e)}")


@router.get("/tts")
async def generate_tts(
    text: str = Query(..., description="要合成语音的文本"),
    voice: Literal["us", "uk"] = Query("us", description="音色：us=美式, uk=英式")
):
    """
    使用有道TTS生成单词发音

    Args:
        text: 要合成的文本（单词或短语）
        voice: 音色选择（us=美式英语，uk=英式英语）

    Returns:
        音频文件流（MP3格式）

    Raises:
        HTTPException: 400 - 参数无效
        HTTPException: 500 - TTS生成失败
    """
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="文本不能为空")

    # 根据voice选择发音人
    voice_name = "youxiaomei" if voice == "us" else "youxiaoying"

    # 生成缓存key（文本+音色）
    cache_key = f"tts_{text}_{voice}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    cache_path = AUDIO_CACHE_DIR / f"{cache_hash}.mp3"

    # 检查缓存
    if cache_path.exists():
        print(f"🎵 [TTS] 从缓存返回: {text} ({voice})")
        return Response(
            content=cache_path.read_bytes(),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )

    # 生成TTS音频
    try:
        client = get_tts_client()
        # V1.5: 调大音量到3.0（正常为1.0，最大5.0）
        audio_data = await client.synthesize_speech(
            text,
            voice_name=voice_name,
            volume="3.0"
        )

        if not audio_data:
            raise HTTPException(status_code=500, detail="TTS音频生成失败")

        # 保存到缓存
        cache_path.write_bytes(audio_data)
        print(f"💾 [TTS] 音频已缓存: {text} ({voice}) - {len(audio_data)} bytes")

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [TTS] 生成异常: {e}")
        raise HTTPException(status_code=500, detail=f"TTS生成失败: {str(e)}")
