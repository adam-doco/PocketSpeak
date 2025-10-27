# -*- coding: utf-8 -*-
"""
豆包语音评分客户端 - PocketSpeak V1.7
调用豆包 AI API进行语音评分分析（性能优化版）
"""

import json
import httpx
from typing import Dict, Optional


class DoubaoSpeechEvalClient:
    """豆包语音评分客户端"""

    def __init__(self, api_key: str, base_url: str, model: str = "ep-default-model", timeout: int = 15):
        """
        初始化豆包评分客户端

        Args:
            api_key: 豆包API密钥（ARK API Key）
            base_url: API基础URL
            model: 使用的模型ID或Endpoint ID
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

        print(f"🔧 豆包客户端初始化: model={model}, base_url={base_url}")

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """
        加载豆包评分提示词模板（V1.7优化版）

        Returns:
            str: 提示词模板
        """
        # V1.7优化: 精简提示词，保持准确性，加快AI响应速度
        # V1.7.1: 强化JSON格式要求，明确所有必需字段
        template = """你是英语评分老师。请严格按照JSON格式返回评分，必须包含所有字段。

句子：{sentence}

返回JSON（不要用```包裹，直接返回纯JSON）：
{{
  "grammar": {{
    "has_error": false,
    "original": "{sentence}",
    "suggestion": "",
    "reason": ""
  }},
  "pronunciation": {{
    "score": 90,
    "words": [{{"word": "Can", "status": "good"}}, {{"word": "I", "status": "good"}}],
    "fluency": 90,
    "clarity": 90,
    "completeness": 100,
    "speed_wpm": 120
  }},
  "expression": {{
    "level": "地道",
    "suggestion": "",
    "reason": ""
  }},
  "overall_score": 90
}}

必须包含的字段：
1. pronunciation.score (发音总分 0-100)
2. pronunciation.words (每个单词的评分数组)
3. pronunciation.fluency (流利度 0-100) ← 必须
4. pronunciation.clarity (清晰度 0-100) ← 必须
5. pronunciation.completeness (完整度 0-100) ← 必须
6. pronunciation.speed_wpm (语速 词/分钟) ← 必须

评分标准：
- status: good/bad/needs_improvement
- level: 不地道/一般/地道/非常地道
- 所有字段都必须返回，不能省略！"""
        return template

    async def evaluate_speech(self, sentence: str) -> Dict:
        """
        评估用户语音句子

        Args:
            sentence: 用户语音识别的文本

        Returns:
            Dict: 评分结果，包含：
                - overall_score: int - 综合得分
                - grammar: Dict - 语法分析
                - pronunciation: Dict - 发音评分
                - expression: Dict - 表达评估
                - error: str - 错误信息(如果失败)
        """
        try:
            print(f"\n🎯 豆包评估语音: {sentence}")

            # 构造提示词
            prompt = self.prompt_template.format(sentence=sentence)

            # 调用豆包API
            response_text = await self._call_doubao_api(prompt)

            if not response_text:
                return {
                    'success': False,
                    'error': '豆包API返回为空'
                }

            # 解析JSON响应
            result = self._parse_response(response_text)

            return result

        except Exception as e:
            print(f"❌ 豆包评估异常: {e}")
            return {
                'success': False,
                'error': f'评估失败: {str(e)}'
            }

    async def _call_doubao_api(self, prompt: str) -> Optional[str]:
        """
        调用豆包API

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
                        'role': 'system',
                        'content': '你是一位专业的英语语音评分老师。请始终返回标准JSON格式。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.1,  # V1.7性能优化: 降低随机性加快生成
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    print(f"❌ 豆包API错误: HTTP {response.status_code}")
                    print(f"   响应: {response.text}")
                    return None

                data = response.json()

                # 提取返回内容
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    print(f"✅ 豆包返回: {len(content)}字符")
                    return content
                else:
                    print(f"❌ 豆包返回格式异常: {data}")
                    return None

        except Exception as e:
            print(f"❌ 豆包API调用异常: {e}")
            return None

    def _parse_response(self, response_text: str) -> Dict:
        """
        解析豆包返回的JSON

        Args:
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
            required_fields = ['overall_score', 'grammar', 'pronunciation', 'expression']
            for field in required_fields:
                if field not in data:
                    print(f"⚠️ 豆包返回缺少必要字段: {field}")
                    return {
                        'success': False,
                        'error': f'AI返回数据缺少字段: {field}'
                    }

            print(f"✅ 评分解析成功: 综合得分 {data['overall_score']}")

            return {
                'success': True,
                **data
            }

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   原始文本: {response_text[:200]}...")
            return {
                'success': False,
                'error': f'AI返回格式错误: {str(e)}'
            }
        except Exception as e:
            print(f"❌ 解析响应异常: {e}")
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
