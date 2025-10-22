# -*- coding: utf-8 -*-
"""
有道翻译API客户端 - PocketSpeak V1.5
调用有道智云翻译API查询单词释义
"""

import hashlib
import uuid
import time
import httpx
from typing import Dict, List, Optional


class YoudaoClient:
    """有道翻译API客户端"""

    def __init__(self, app_id: str, app_key: str, base_url: str, timeout: int = 10):
        """
        初始化有道客户端

        Args:
            app_id: 有道应用ID
            app_key: 有道应用密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = base_url
        self.timeout = timeout

    def _generate_sign(self, query: str, salt: str, curtime: str) -> str:
        """
        生成签名（有道API v3要求）

        签名算法：SHA256(appKey + input + salt + curtime + appSecret)
        其中 input = q（如果q长度<=20）或 q前10个字符 + q长度 + q后10个字符

        Args:
            query: 查询文本
            salt: 随机盐值
            curtime: 当前时间戳（秒）

        Returns:
            str: SHA256签名
        """
        # 计算 input
        q_len = len(query)
        if q_len <= 20:
            input_str = query
        else:
            input_str = query[:10] + str(q_len) + query[-10:]

        # 生成签名（使用SHA256）
        sign_str = f"{self.app_id}{input_str}{salt}{curtime}{self.app_key}"
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    async def lookup_word(self, word: str) -> Dict:
        """
        查询单词释义（纯有道API策略）

        Args:
            word: 要查询的英文单词

        Returns:
            Dict: 查询结果，包含：
                - success: bool - 是否成功
                - word: str - 单词
                - phonetic: Dict - 音标
                - definitions: List[str] - 释义列表
                - error: str - 错误信息（如果失败）

        Raises:
            Exception: API调用失败
        """
        try:
            print(f"\n🔍 查询单词: {word}")

            # V1.5优化：只使用有道API（一次调用获取所有数据）
            result = await self._get_definitions_from_youdao(word)

            if not result.get('success'):
                return {
                    'success': False,
                    'word': word,
                    'error': '查询失败'
                }

            return result

        except Exception as e:
            print(f"❌ 查询单词异常: {e}")
            return {
                'success': False,
                'word': word,
                'error': f'查询失败: {str(e)}'
            }

    async def _get_phonetic_from_free_dict(self, word: str) -> Dict:
        """从免费词典API获取音标和音频URL（V1.5优化：智能回退策略）"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
                data = response.json()

            if isinstance(data, list) and len(data) > 0:
                word_data = data[0]
                phonetics = word_data.get('phonetics', [])

                us_phonetic = ''
                uk_phonetic = ''
                us_audio = ''
                uk_audio = ''
                fallback_audio = ''  # 备用音频（如果US/UK都没有）

                # V1.5: 收集音标
                for p in phonetics:
                    text = p.get('text', '')
                    audio = p.get('audio', '')

                    if text:
                        if 'us' in audio.lower() or 'american' in audio.lower():
                            us_phonetic = text
                        elif 'uk' in audio.lower() or 'british' in audio.lower():
                            uk_phonetic = text
                        elif not us_phonetic:
                            us_phonetic = text

                # 第二次遍历：收集音频（不依赖音标）
                for p in phonetics:
                    audio = p.get('audio', '')

                    if audio:
                        # 根据URL关键词判断
                        if '-us.' in audio or '-us-' in audio or 'american' in audio.lower():
                            us_audio = audio
                        elif '-uk.' in audio or '-uk-' in audio or 'british' in audio.lower():
                            uk_audio = audio
                        elif '-ca.' in audio or 'canada' in audio.lower():
                            # 加拿大发音接近美式
                            if not us_audio:
                                us_audio = audio
                        elif '-au.' in audio or 'australia' in audio.lower():
                            # 澳大利亚发音接近英式
                            if not uk_audio:
                                uk_audio = audio
                        elif not fallback_audio:
                            # 保存第一个音频作为备用
                            fallback_audio = audio

                # V1.5: 智能回退 - 如果某个口音没有音频，使用另一个或备用
                if not us_audio:
                    us_audio = uk_audio or fallback_audio
                if not uk_audio:
                    uk_audio = us_audio or fallback_audio

                # 如果只有一个音标，两边都用它
                if us_phonetic and not uk_phonetic:
                    uk_phonetic = us_phonetic
                elif uk_phonetic and not us_phonetic:
                    us_phonetic = uk_phonetic

                # V1.5: 提取详细释义（meanings字段）
                detailed_definitions = []
                meanings = word_data.get('meanings', [])

                for meaning in meanings[:3]:  # 最多取3种词性
                    part_of_speech = meaning.get('partOfSpeech', '')
                    definitions = meaning.get('definitions', [])

                    for idx, def_item in enumerate(definitions[:2]):  # 每种词性最多2个释义
                        definition = def_item.get('definition', '')
                        if definition:
                            # 构造格式：[词性] 定义
                            detailed_definitions.append(f"[{part_of_speech}] {definition}")

                print(f"📖 音标: US={us_phonetic}, UK={uk_phonetic}")
                print(f"📝 详细释义数: {len(detailed_definitions)}")

                return {
                    'us': us_phonetic,
                    'uk': uk_phonetic,
                    'us_audio': us_audio,
                    'uk_audio': uk_audio,
                    'detailed_definitions': detailed_definitions  # 返回英文详细释义
                }

        except Exception as e:
            print(f"⚠️ 获取音标失败: {e}")

        return {'us': '', 'uk': '', 'us_audio': '', 'uk_audio': ''}

    async def _translate_text(self, text: str) -> str:
        """
        翻译文本（英文->中文）

        Args:
            text: 要翻译的英文文本

        Returns:
            str: 翻译后的中文，失败返回空字符串
        """
        try:
            salt = str(uuid.uuid4())
            curtime = str(int(time.time()))
            sign = self._generate_sign(text, salt, curtime)

            params = {
                'q': text,
                'from': 'en',
                'to': 'zh-CHS',
                'appKey': self.app_id,
                'salt': salt,
                'sign': sign,
                'signType': 'v3',
                'curtime': curtime
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                data = response.json()

            error_code = data.get('errorCode', '0')
            if error_code == '0' and 'translation' in data:
                return data['translation'][0]

            return ''

        except Exception as e:
            print(f"⚠️ 翻译失败: {e}")
            return ''

    async def _get_definitions_from_youdao(self, word: str) -> Dict:
        """从有道API获取中文释义"""
        try:
            # 生成请求参数
            salt = str(uuid.uuid4())
            curtime = str(int(time.time()))
            sign = self._generate_sign(word, salt, curtime)

            params = {
                'q': word,
                'from': 'en',
                'to': 'zh-CHS',
                'appKey': self.app_id,
                'salt': salt,
                'sign': sign,
                'signType': 'v3',
                'curtime': curtime
            }

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                data = response.json()

            # 检查错误码
            error_code = data.get('errorCode', '0')
            if error_code != '0':
                error_msg = self._get_error_message(error_code)
                print(f"❌ 有道API错误: {error_code} - {error_msg}")
                return {'definitions': []}

            # V1.5：打印有道API完整返回，方便调试
            print(f"📋 有道API返回数据:")
            print(f"   - errorCode: {error_code}")
            print(f"   - translation: {data.get('translation', [])}")
            print(f"   - basic: {data.get('basic', {})}")
            print(f"   - web: {len(data.get('web', []))}条")

            # 解析结果
            result = self._parse_response(word, data)
            print(f"✅ 查询成功: {word}, 释义数: {len(result.get('definitions', []))}")
            return result

        except Exception as e:
            print(f"❌ 获取释义失败: {e}")
            return {'definitions': []}

    def _parse_response(self, word: str, data: Dict) -> Dict:
        """
        解析有道API响应（V1.5：完整利用所有字段）

        Args:
            word: 查询的单词
            data: API响应数据

        Returns:
            Dict: 解析后的结果
        """
        # 提取基础释义
        basic = data.get('basic', {})

        # 提取音标
        phonetic = {
            'us': basic.get('us-phonetic', ''),
            'uk': basic.get('uk-phonetic', '')
        }

        # 如果没有区分英美音标，使用通用音标
        if not phonetic['us'] and not phonetic['uk']:
            phonetic['us'] = basic.get('phonetic', '')
            phonetic['uk'] = basic.get('phonetic', '')

        # V1.5优化：提取释义（优先级：basic.explains > translation > web）
        definitions = []

        # 1. 优先使用 basic.explains（详细释义，已包含词性）
        if 'explains' in basic and basic['explains']:
            definitions = basic['explains']
            print(f"✅ 使用basic.explains: {len(definitions)}条释义")

        # 2. 备用：使用 translation（简单翻译）
        elif 'translation' in data and data['translation']:
            definitions = data['translation']
            print(f"⚠️ 只有translation字段: {definitions}")

        # 3. 最后尝试：从web释义中提取
        elif 'web' in data and data['web']:
            web_definitions = []
            for web_item in data.get('web', [])[:3]:  # 最多取3条
                if 'value' in web_item:
                    web_definitions.append('；'.join(web_item['value']))
            if web_definitions:
                definitions = web_definitions
                print(f"⚠️ 使用web释义: {len(definitions)}条")

        # 如果还是没有释义，使用单词本身
        if not definitions:
            definitions = [word]
            print(f"❌ 无任何释义，使用单词本身")

        return {
            'success': True,
            'word': word,
            'phonetic': phonetic,
            'definitions': definitions
        }

    def _get_error_message(self, error_code: str) -> str:
        """
        根据错误码返回错误信息

        Args:
            error_code: 有道API错误码

        Returns:
            str: 错误信息
        """
        error_messages = {
            '101': '缺少必填的参数',
            '102': '不支持的语言类型',
            '103': '翻译文本过长',
            '104': '不支持的API类型',
            '105': '不支持的签名类型',
            '106': '不支持的响应类型',
            '107': '不支持的传输加密类型',
            '108': '应用ID无效',
            '109': 'batchLog格式不正确',
            '110': '无相关服务的有效实例',
            '111': '开发者账号无效',
            '113': 'q不能为空',
            '201': '解密失败',
            '202': '签名检验失败',
            '203': '访问IP地址不在可访问IP列表',
            '301': '辞典查询失败',
            '302': '翻译查询失败',
            '303': '服务端的其它异常',
            '401': '账户已经欠费',
            '411': '访问频率受限'
        }

        return error_messages.get(error_code, f'未知错误（错误码：{error_code}）')
