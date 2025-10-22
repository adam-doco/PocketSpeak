# -*- coding: utf-8 -*-
"""
有道语音合成(TTS)客户端 - PocketSpeak V1.5
调用有道智云TTS API生成单词发音
"""

import hashlib
import uuid
import time
import httpx
from typing import Optional, Literal


class YoudaoTTSClient:
    """有道TTS API客户端"""

    def __init__(self, app_id: str, app_key: str, timeout: int = 10):
        """
        初始化TTS客户端

        Args:
            app_id: 有道应用ID
            app_key: 有道应用密钥
            timeout: 请求超时时间（秒）
        """
        self.app_id = app_id
        self.app_key = app_key
        self.timeout = timeout
        self.tts_url = "https://openapi.youdao.com/ttsapi"

    def _generate_sign(self, text: str, salt: str, curtime: str) -> str:
        """
        生成签名（v3签名方式）

        Args:
            text: 要合成的文本
            salt: 随机盐值
            curtime: 当前时间戳（秒）

        Returns:
            str: SHA256签名
        """
        # 计算 input（与翻译API相同逻辑）
        q_len = len(text)
        if q_len <= 20:
            input_str = text
        else:
            input_str = text[:10] + str(q_len) + text[-10:]

        # 生成签名: sha256(应用ID + input + salt + curtime + 应用密钥)
        sign_str = f"{self.app_id}{input_str}{salt}{curtime}{self.app_key}"
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    async def synthesize_speech(
        self,
        text: str,
        voice_name: Literal["youxiaomei", "youxiaoying"] = "youxiaomei",
        speed: str = "1",
        volume: str = "1.00"
    ) -> Optional[bytes]:
        """
        合成语音

        Args:
            text: 要合成的文本（单词或短语）
            voice_name: 发音人名字
                - youxiaomei: 美式英语女声
                - youxiaoying: 英式英语女声
            speed: 语速（0.5-2.0，默认1为正常速度）
            volume: 音量（0.50-5.00，默认1.00）

        Returns:
            bytes: 音频数据（MP3格式），失败返回None
        """
        try:
            # 生成请求参数
            salt = str(uuid.uuid4())
            curtime = str(int(time.time()))
            sign = self._generate_sign(text, salt, curtime)

            # 构建POST表单数据
            data = {
                'q': text,
                'appKey': self.app_id,
                'salt': salt,
                'sign': sign,
                'signType': 'v3',
                'curtime': curtime,
                'voiceName': voice_name,
                'format': 'mp3',
                'speed': speed,
                'volume': volume
            }

            print(f"🔊 [TTS] 合成语音: '{text}' (发音人:{voice_name})")

            # 发送POST请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.tts_url, data=data)

                # 检查响应类型
                content_type = response.headers.get('Content-Type', '')

                if 'audio' in content_type:
                    # 成功：返回音频数据
                    audio_data = response.content
                    print(f"✅ [TTS] 合成成功: {len(audio_data)} bytes")
                    return audio_data
                else:
                    # 失败：返回JSON错误响应
                    try:
                        error_data = response.json()
                        error_code = error_data.get('errorCode', 'unknown')
                        print(f"❌ [TTS] 合成失败: errorCode={error_code}")
                    except:
                        print(f"❌ [TTS] 合成失败: {response.status_code} - {response.text[:200]}")
                    return None

        except Exception as e:
            print(f"❌ [TTS] 合成异常: {e}")
            return None
