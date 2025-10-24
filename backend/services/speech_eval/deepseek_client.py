# -*- coding: utf-8 -*-
"""
DeepSeek语音评分客户端 - PocketSpeak V1.6
调用DeepSeek AI API进行语音评分分析
"""

import json
import httpx
from typing import Dict, Optional


class DeepSeekSpeechEvalClient:
    """DeepSeek语音评分客户端"""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat", timeout: int = 30):
        """
        初始化DeepSeek评分客户端

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 使用的模型名称
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """
        加载DeepSeek评分提示词模板

        Returns:
            str: 提示词模板
        """
        # 根据PRD文档定义的提示词
        template = """# 🎯 任务指令（请勿修改）
你是一位专业的英语语音评分老师，请根据以下句子内容，评估用户英语表达的准确性、流畅性和地道程度，并返回结构化结果。

## 句子内容：
{sentence}

## 要求：
请从以下三个维度评分，并返回标准 JSON 格式结果：

1. 语法分析（grammar）：
- 判断句子是否有语法错误（true/false）
- 若有错误，请指出原句、建议句子和错误原因

2. 发音评分（pronunciation）：
- 给出发音整体分数（0-100）
- 给出每个单词的发音状态（"good", "bad", "needs_improvement"）
- 分别给出流利度、清晰度、完整度（0-100）
- 推测语速（单位：词/分钟）

3. 表达地道程度（expression）：
- 是否地道表达（"不地道", "一般", "地道", "非常地道"）
- 若表达不够地道，请给出优化建议及原因说明

## 返回格式（务必返回标准 JSON）：
{{
  "grammar": {{
    "has_error": true,
    "original": "What is hobbies?",
    "suggestion": "What are your hobbies?",
    "reason": "hobbies 为复数，应搭配 are，而不是 is"
  }},
  "pronunciation": {{
    "score": 89,
    "words": [
      {{"word": "What", "status": "good"}},
      {{"word": "is", "status": "good"}},
      {{"word": "hobbies", "status": "bad"}}
    ],
    "fluency": 96,
    "clarity": 88,
    "completeness": 100,
    "speed_wpm": 102
  }},
  "expression": {{
    "level": "地道",
    "suggestion": "What are your hobbies?",
    "reason": "标准美式问法，更自然"
  }},
  "overall_score": 91
}}"""
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
            print(f"\n🎯 DeepSeek评估语音: {sentence}")

            # 构造提示词
            prompt = self.prompt_template.format(sentence=sentence)

            # 调用DeepSeek API
            response_text = await self._call_deepseek_api(prompt)

            if not response_text:
                return {
                    'success': False,
                    'error': 'DeepSeek API返回为空'
                }

            # 解析JSON响应
            result = self._parse_response(response_text)

            return result

        except Exception as e:
            print(f"❌ DeepSeek评估异常: {e}")
            return {
                'success': False,
                'error': f'评估失败: {str(e)}'
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
                'max_tokens': 800,  # 评分需要更多token
                'temperature': 0.3,
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

    def _parse_response(self, response_text: str) -> Dict:
        """
        解析DeepSeek返回的JSON

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
                    print(f"⚠️ DeepSeek返回缺少必要字段: {field}")
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
