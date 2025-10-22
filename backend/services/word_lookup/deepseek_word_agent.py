# -*- coding: utf-8 -*-
"""
DeepSeek单词查询Agent - PocketSpeak V1.5.1
调用DeepSeek AI生成单词释义和联想记忆
"""

import json
import httpx
from typing import Dict, List, Optional
from pathlib import Path


class DeepSeekWordAgent:
    """DeepSeek AI单词查询Agent"""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat", timeout: int = 30, max_tokens: int = 500):
        """
        初始化DeepSeek Agent

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 使用的模型名称
            timeout: 请求超时时间（秒）
            max_tokens: 最大返回token数
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """
        从提示词文档加载模板

        Returns:
            str: 提示词模板
        """
        # 定义默认模板（精简版 - 性能优化）
        template = """查询单词"{word}"，返回JSON格式：

{{
  "word": "{word}",
  "us_phonetic": "美式音标IPA",
  "uk_phonetic": "英式音标IPA",
  "definitions": [{{"pos": "词性", "meaning": "中文释义"}}],
  "mnemonic": "简洁的记忆技巧"
}}

要求：
1. 只返回JSON,无额外文字
2. 音标用IPA格式(如/test/)
3. definitions最多3-4条
4. mnemonic一句话即可
5. 释义简洁明了"""

        return template

    async def lookup_word(self, word: str) -> Dict:
        """
        查询单词释义和联想记忆

        Args:
            word: 要查询的英文单词

        Returns:
            Dict: 查询结果，包含：
                - success: bool - 是否成功
                - word: str - 单词
                - definitions: List[Dict] - 释义列表 [{"pos": "词性", "meaning": "释义"}]
                - mnemonic: str - 联想记忆
                - error: str - 错误信息（如果失败）
        """
        try:
            print(f"\n🤖 DeepSeek查询单词: {word}")

            # 构造提示词
            prompt = self.prompt_template.format(word=word)

            # 调用DeepSeek API
            response_text = await self._call_deepseek_api(prompt)

            if not response_text:
                return {
                    'success': False,
                    'word': word,
                    'error': 'DeepSeek API返回为空'
                }

            # 解析JSON响应
            result = self._parse_response(word, response_text)

            return result

        except Exception as e:
            print(f"❌ DeepSeek查询异常: {e}")
            return {
                'success': False,
                'word': word,
                'error': f'查询失败: {str(e)}'
            }

    async def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """
        调用DeepSeek API

        Args:
            prompt: 提示词

        Returns:
            Optional[str]: API返回的文本，失败返回None
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': 0.3,  # 降低温度以获得更一致的输出
                'response_format': {'type': 'json_object'}  # 强制返回JSON
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    print(f"❌ DeepSeek API错误: HTTP {response.status_code}")
                    print(f"   响应: {response.text}")
                    return None

                data = response.json()

                # 提取返回内容
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    print(f"✅ DeepSeek返回: {len(content)}字符")
                    return content
                else:
                    print(f"❌ DeepSeek返回格式异常: {data}")
                    return None

        except Exception as e:
            print(f"❌ DeepSeek API调用异常: {e}")
            return None

    def _parse_response(self, word: str, response_text: str) -> Dict:
        """
        解析DeepSeek返回的JSON

        Args:
            word: 查询的单词
            response_text: API返回的文本

        Returns:
            Dict: 解析后的结果
        """
        try:
            # 清理可能的markdown代码块标记
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # 解析JSON
            data = json.loads(cleaned_text)

            # 验证必要字段
            if 'definitions' not in data or 'mnemonic' not in data:
                print(f"⚠️ DeepSeek返回缺少必要字段: {data}")
                return {
                    'success': False,
                    'word': word,
                    'error': 'AI返回数据格式不完整'
                }

            print(f"✅ 解析成功: {len(data['definitions'])}条释义")

            return {
                'success': True,
                'word': data.get('word', word),
                'us_phonetic': data.get('us_phonetic', ''),
                'uk_phonetic': data.get('uk_phonetic', ''),
                'definitions': data['definitions'],
                'mnemonic': data['mnemonic']
            }

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   原始文本: {response_text[:200]}...")
            return {
                'success': False,
                'word': word,
                'error': f'AI返回格式错误: {str(e)}'
            }
        except Exception as e:
            print(f"❌ 解析响应异常: {e}")
            return {
                'success': False,
                'word': word,
                'error': f'解析失败: {str(e)}'
            }
