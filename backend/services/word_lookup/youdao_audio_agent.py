# -*- coding: utf-8 -*-
"""
有道音频Agent - PocketSpeak V1.5.1
生成单词的音标和音频链接（使用有道TTS）
"""

from typing import Dict


class YoudaoAudioAgent:
    """有道音频Agent - 生成音标和音频URL"""

    def __init__(self, app_id: str, app_key: str):
        """
        初始化有道音频Agent

        Args:
            app_id: 有道应用ID
            app_key: 有道应用密钥
        """
        self.app_id = app_id
        self.app_key = app_key

    async def get_phonetics_and_audio(self, word: str) -> Dict:
        """
        获取单词的音标和音频URL

        V1.5.1策略：
        - 音标由DeepSeek AI生成（暂时返回空，后续可扩展）
        - 音频使用有道TTS生成（复用已有的/api/audio/tts接口）

        Args:
            word: 要查询的英文单词

        Returns:
            Dict: 包含音标和音频URL
                - uk_phonetic: str - 英式音标（暂时为空）
                - us_phonetic: str - 美式音标（暂时为空）
                - uk_audio_url: str - 英式发音URL
                - us_audio_url: str - 美式发音URL
        """
        try:
            print(f"🔊 生成音频URL: {word}")

            # V1.5.1: 音频URL直接指向TTS接口（已在audio_proxy中实现）
            result = {
                'uk_phonetic': '',  # 暂时为空，DeepSeek不返回音标
                'us_phonetic': '',  # 暂时为空
                'uk_audio_url': f'/api/audio/tts?text={word}&voice=uk',
                'us_audio_url': f'/api/audio/tts?text={word}&voice=us'
            }

            print(f"✅ 音频URL生成成功")
            return result

        except Exception as e:
            print(f"❌ 生成音频URL异常: {e}")
            return {
                'uk_phonetic': '',
                'us_phonetic': '',
                'uk_audio_url': '',
                'us_audio_url': ''
            }
