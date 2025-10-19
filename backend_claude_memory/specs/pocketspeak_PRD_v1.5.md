

📘 PocketSpeak V1.5 产品需求文档（PRD）

版本号：v1.5
更新时间：2025-09-29
负责人：用户（PM）
执行者：Claude + Flutter 前端 + FastAPI 后端

⸻

🎯 V1.5 版本目标：

提升学习效率，优化用户在与 AI 对话中的“生词处理”体验。

⸻

🧩 一、核心功能概述

功能模块	说明
📖 单词点击释义	聊天过程中，用户点击陌生单词，即可查看中英文释义、音标、发音按钮，并可加入生词本
🔊 发音播放	用户可点击英式 / 美式音标旁的按钮，收听对应发音（从第三方 TTS 服务获取）
📚 生词本系统（基础版）	用户可点击“加入生词本”，将单词及释义收藏（后续版本可加入生词本页面）
🔧 API配置模块	所有第三方服务（词典、TTS 等）通过 YAML 文件集中配置，可支持后期切换多个 API


⸻

📱 二、页面设计

1. 聊天页单词弹窗（Word Definition Bottom Sheet）
	•	触发方式：用户在 AI 聊天内容中点击任意英文单词
	•	展现方式：底部弹窗（Bottom Sheet）
	•	展示内容：

元素	描述
🔠 单词本体	例如：“reluctant”（加粗）
🈯 中文释义	支持多个释义条目，来源如有道、Oxford API
📖 英式音标	/rɪˈlʌktənt/ + 发音按钮
📖 美式音标	/rɪˈlʌktənt/ + 发音按钮
➕ 加入生词本	可点击按钮，调用后端接口加入收藏列表
❌ 关闭按钮	关闭弹窗


⸻

🧠 三、用户交互流程

graph TD
A[用户点击单词] --> B[前端捕获词语并请求词义接口]
B --> C[后端调用 dictionary API]
C --> D[返回释义 + 音标 + TTS音频地址]
D --> E[前端渲染弹窗]
E --> F[点击播放按钮 -> 播放音频]
E --> G[点击加入生词本 -> 调用收藏API]


⸻

🔌 四、接口设计（后端）

1. 查询单词释义接口
	•	GET /api/words/lookup
	•	参数：word=string
	•	返回示例：

{
  "word": "reluctant",
  "phonetic": {
    "uk": "/rɪˈlʌktənt/",
    "us": "/rɪˈlʌktənt/"
  },
  "audio": {
    "uk": "https://xxx/reluctant_uk.mp3",
    "us": "https://xxx/reluctant_us.mp3"
  },
  "definitions": [
    "不情愿的，勉强的",
    "犹豫的，迟疑的"
  ]
}


⸻

2. 加入生词本接口
	•	POST /api/words/favorite
	•	Body：

{
  "user_id": "abc123",
  "word": "reluctant"
}

	•	返回：{"status": "ok"}

⸻

🔧 五、API配置模块设计

📁 结构建议：

backend/
└── config/
    └── external_apis.yaml         # 所有第三方 API 配置
    └── api_loader.py              # API动态加载器

🧾 external_apis.yaml 示例：

dictionary:
  provider: youdao
  youdao:
    app_id: "xxxxx"
    app_key: "yyyyy"
    endpoint: "https://openapi.youdao.com/api"
  free_dictionary:
    endpoint: "https://api.dictionaryapi.dev/api/v2/entries/en"

tts:
  provider: google
  google:
    api_key: "zzz"
    endpoint: "https://texttospeech.googleapis.com/v1/..."


⸻

🔧 六、数据库结构（生词表）

字段名	类型	描述
id	string	唯一标识
user_id	string	用户ID
word	string	单词原文
created_at	datetime	收藏时间


⸻

✅ 七、技术实现要点
	•	第三方词典建议优先使用：
	•	免费优先：DictionaryAPI, Free Dictionary
	•	商业授权备用：有道、有道词典海外版、Oxford API
	•	音频格式统一为 MP3（确保兼容 iOS + Android 播放）
	•	Claude 在调用 API 时必须通过 api_loader.py 读取配置，禁止硬编码

⸻

📈 八、未来可拓展点

模块	说明
生词本页面	展示用户收藏的所有单词，可分类、打标签、学习
单词练习	基于生词生成填空题、听写等练习
AI语义解释	Claude 自动用英文解释生词（初中高级词汇适配）


