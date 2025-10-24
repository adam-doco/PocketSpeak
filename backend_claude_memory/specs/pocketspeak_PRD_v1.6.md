

📄 PocketSpeak V1.6 PRD — 用户语音评分系统（最终版）

版本号：V1.6
发布日期：2025-10-22
版本类型：功能增强
负责人：Claude
引用规范：
	•	claude_memory/specs/naming_convention.md
	•	claude_memory/specs/worklog_template.md
	•	backend_claude_memory/prompts/deepseek_speech_feedback_prompt.md

⸻

🎯 一、版本目标

为用户发送的语音进行多维度评分反馈，包括：
	•	语法准确性分析
	•	发音细节评分（数字分数 + 流利度、语速等维度）
	•	地道表达判断与优化建议

帮助用户明确自己语音表达的问题，获取可执行的提升建议。

⸻

📱 二、页面交互设计（对标示例图）

2.1 聊天页面新增评分功能
	•	用户每次发送语音后，自动展示主评分卡片（如下图绿色区域形式）：

综合得分：93分
- 语法：❗️（有问题，点击查看）
- 发音：89分（点击进入发音分析详情）
- 表达地道程度：地道（点击查看更地道表达建议）


	•	所有子项都可点击，打开对应弹窗查看详细分析内容。

⸻

🔍 三、评分详情弹窗（对标参考图二）

3.1 发音分析弹窗（点击“发音分”按钮）

内容结构完全仿照示例图第二张图：
	•	发音逐词打分（用绿线标记正确发音部分，红点提示错误词）
	•	示例：What is hobbies?
	•	What ✅
	•	is ✅
	•	Hobbies 🔴（待提高）
	•	发音样本对比播放
	•	英音：🔊 播放按钮
	•	美音：🔊 播放按钮
	•	用户发音：🔊
	•	细分评分
	•	流利度：98
	•	发音清晰度：91
	•	语速：94 词/分钟（显示仪表盘图标）
	•	完整度：100
	•	系统建议文本
	•	例如：发音纯正，堪比母语者表达

⸻

3.2 语法错误弹窗（点击 ❗️ 图标）
	•	原始句子：
What is hobbies?
	•	修改建议：
What are your hobbies?
	•	AI解释：
hobbies 为复数，应使用 are 而非 is，同时首字母不需大写。

⸻

3.3 表达优化弹窗（点击表达等级）
	•	当前表达：
I like to watch movie in my free time.
	•	建议表达：
I enjoy watching movies when I have some spare time.
	•	AI解释：
enjoy watching 更符合日常地道表达，“spare time” 更自然。

⸻

🧠 四、评分逻辑与规则

4.1 主评分逻辑（综合分数）
	•	综合评分 0-100 分，由以下加权计算得出：
	•	发音：40%
	•	语法：30%
	•	表达地道度：30%

4.2 发音评分来源
	•	通过 deepseek 的音频评分接口（或自建 Whisper 识别 + 模型评分）
	•	字词级评分
	•	输出包括：每词状态、全句指标、语速统计

⸻

🔗 五、接口设计（后端）

5.1 POST /api/eval/speech-feedback

请求体：

{
  "audio_file": <用户语音>,
  "transcript": "I like to watch movie in my free time"
}

返回体（简化结构）：

{
  "overall_score": 93,
  "grammar": {
    "has_error": true,
    "original": "What is hobbies?",
    "suggestion": "What are your hobbies?",
    "reason": "主谓不一致 + 名词复数错误"
  },
  "pronunciation": {
    "score": 89,
    "words": [
      {"word": "What", "status": "good"},
      {"word": "is", "status": "good"},
      {"word": "hobbies", "status": "bad"}
    ],
    "fluency": 98,
    "clarity": 91,
    "completeness": 100,
    "speed_wpm": 94
  },
  "expression": {
    "level": "地道",
    "suggestion": "I enjoy watching movies when I have some spare time.",
    "reason": "符合美式表达习惯，'enjoy' 更自然"
  }
}


⸻

📦 六、数据存储与缓存策略
	•	表名：speech_eval_results
	•	字段：
	•	user_id
	•	sentence
	•	overall_score
	•	grammar_error
	•	pronunciation_score
	•	expression_level
	•	raw_json
	•	created_at
	•	本地缓存策略：对相同语音+文本避免重复调用 API（节省成本）

⸻

🔐 七、API 接入说明
	•	使用 Deepseek 的 专属评分 API Key
	•	配置路径：config/api_config.py
	•	不共用释义查询 API，避免 prompt 混乱

⸻

✅ 八、交付验收标准
	•	语音识别 + 三维分析时间 < 3s
	•	各子弹窗能完整、清晰展示评分维度
	•	整体评分逻辑清晰，用户可感知提升方向
	•	前端评分 UI 界面高度还原参考图，结构清晰

⸻
