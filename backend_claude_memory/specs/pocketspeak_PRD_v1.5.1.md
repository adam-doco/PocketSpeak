

📘 PocketSpeak V1.5.1 版本 PRD

功能名称：英文单词点击弹窗查词功能
类型：学习辅助增强功能
所属版本：v1.5.1
作者：@alex
日期：2025-09-30
状态：✅已评审｜🟡开发中｜⬜待测试

⸻

🎯 一、版本目标

在用户与 AI 进行语音或文本对话过程中，用户可能遇到不熟悉的单词。为提升学习体验，本版本支持：
	•	用户点击英文单词时触发查询
	•	自动调取 AI（DeepSeek）返回标准释义 + 联想记忆
	•	自动使用有道词典 API 播放英美发音
	•	前端以弹窗形式展示全部内容
	•	实现后端缓存机制，避免重复查询

⸻

🧩 二、功能流程图

点击英文单词
    ↓
调用 `/api/word/lookup?word=favorite`
    ↓
后端查找缓存 → 命中？→ 返回数据
                     ↓ 否
调用 DeepSeek 接口获取释义与联想记忆
调用 有道API 获取音标与音频链接
组合结果 → 缓存 → 返回前端展示


⸻

🖼️ 三、前端展示样式（示意）

示例单词：favorite

-------------------------------
| favorite                    |
| 英 /ˈfeɪvərɪt/ ▶            |
| 美 /ˈfeɪv(ə)rət/ ▶          |
|-----------------------------|
| 释义：                      |
| ［形容词］最喜爱的；特别受喜爱的 |
| ［名词］特别喜爱的人；受宠的人 |
|-----------------------------|
| 联想记忆：                  |
| 可以把 favorite 拆分为：    |
| favor（喜爱）+ ite（物/人） |
| 即你偏爱它的东西。         |
-------------------------------
| 加入生词本 |   关闭        |
-------------------------------


⸻

🧠 四、后端逻辑需求

🔗 API 接口定义

GET /api/word/lookup?word=favorite

返回格式：

{
  "word": "favorite",
  "uk_phonetic": "/ˈfeɪvərɪt/",
  "us_phonetic": "/ˈfeɪv(ə)rət/",
  "uk_audio_url": "https://.../uk.mp3",
  "us_audio_url": "https://.../us.mp3",
  "definitions": [
    {
      "pos": "形容词",
      "meaning": "最喜爱的；特别受喜爱的"
    },
    {
      "pos": "名词",
      "meaning": "特别喜爱的人；受宠的人；得到偏爱的人"
    }
  ],
  "mnemonic": "可以把'favorite'拆分成'favor'（喜爱）和'ite'（表示人或物），想象你最喜爱的东西就是那个你一直偏爱的它。",
  "source": "AI + 有道API",
  "created_at": "2025-09-30T12:00:00"
}


⸻

🧠 Claude 提示词设计要求

创建 Prompt 文档路径：

📄 backend_claude_memory/prompts/word_lookup_prompt.md

提示词内容示例：

你是一个专业的英汉词典，请帮我查询英文单词 “{word}”，并返回以下 JSON 格式（注意，除了以下内容外不要返回任何无关内容！非常重要！）：

{
  "word": "favorite",
  "definitions": [
    {
      "pos": "形容词",
      "meaning": "最喜爱的；特别受喜爱的"
    },
    {
      "pos": "名词",
      "meaning": "特别喜爱的人；受宠的人；得到偏爱的人"
    }
  ],
  "mnemonic": "可以把'favorite'拆分成'favor'（喜爱）和'ite'（表示人或物），想象你最喜爱的东西就是那个你一直偏爱的它。"
}

❗ 注意：音标、发音链接由程序另行调用有道API生成，不需要 AI 返回。

⸻

🧾 五、系统模块拆分

模块名	文件路径	功能描述
Claude提示词	backend_claude_memory/prompts/word_lookup_prompt.md	控制 DeepSeek 输出格式
AI Agent	services/word_lookup/deepseek_word_agent.py	调用 DeepSeek 并解析结果
音标/发音	services/word_lookup/youdao_audio_agent.py	调用有道 API 获取音标与链接
接口路由	routers/word_lookup.py	提供 RESTful API
缓存逻辑	models/word_model.py + db操作	存储已查单词到本地数据库
配置文件	config/api_keys.yaml	配置 DeepSeek 和有道的 API key


⸻

🗃️ 数据库模型设计

class WordEntry(Base):
    __tablename__ = "word_entries"
    id = Column(Integer, primary_key=True)
    word = Column(String, index=True)
    uk_phonetic = Column(String)
    us_phonetic = Column(String)
    uk_audio_url = Column(String)
    us_audio_url = Column(String)
    definitions = Column(JSON)  # List of { pos, meaning }
    mnemonic = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


⸻

🔐 配置要求

新增配置文件：

📄 config/api_keys.yaml

deepseek:
  api_key: sk-xxxxxxxxxxxxxxxx

youdao:
  app_id: xxxxxxxx
  secret: xxxxxxxx


⸻

📌 附加说明
	•	之前已经完成的有道API的相关功能可以保留，只是暂时不使用，后续如需更换为商业词典 API，可保留此模块架构，仅更换 agent 与提示词；
	•	可扩展为每日一句 / 生词本 / AI语义记忆模块。

⸻
