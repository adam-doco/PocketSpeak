

✅ Claude 命名规范（适用于 PocketSpeak 项目）

📁 建议存放路径：claude_memory/specs/naming_convention.md

⸻

🎯 目的

为确保 Claude Code 在开发过程中输出统一、清晰、易维护的代码和文件，特制定本命名规范，适用于 PocketSpeak 项目的全部前后端命名规则。

⸻

🧠 背景说明
	•	本项目基于 小智 AI 协议 构建英语语音学习 App；
	•	采用前后端分离架构：前端为 Web（Flutter Web），后端为 FastAPI；
	•	使用 Claude 进行持续开发，因此需要标准化所有命名格式，以便长期可维护和协作顺畅。

⸻

🧱 统一命名规范（适用于前端、后端、文件系统、变量等）

项目类型	命名格式	示例	说明
Python 变量 / 函数	snake_case	generate_prompt(), user_message_id	遵循 PEP8 标准
Python 类名	PascalCase	ChatSession, XiaoZhiClient	每个类单一职责
Python 模块名	snake_case.py	audio_handler.py, tts_client.py	文件名全小写
配置字段（YAML / env）	UPPER_SNAKE_CASE	XFYUN_APPID, LLM_PROVIDER	全大写 + 下划线分隔
JS / TS 变量名	camelCase	audioStream, chatHistory	遵循 JS 标准
JS / TS 类名	PascalCase	VoiceRecorder, AudioPlayer	类/组件使用 Pascal
React 组件名	PascalCase	ChatBox, Waveform	与文件名保持一致
文件夹命名	kebab-case	core-utils, voice-ui	便于阅读和 URL 路径处理
API 路径	kebab-case	/generate-tts, /upload-audio	避免大小写混淆
WebSocket 类型字段	snake_case	mcp, listen, tts_response	与小智协议保持一致
枚举 / 常量	UPPER_SNAKE_CASE	VOICE_MODE, ERROR_TIMEOUT	所有常量必须全大写
日志记录文件名	yyyy-mm-dd_event_name.log	2025-09-25_voice_debug.log	日期靠前，便于归档


⸻

📚 Claude 专属约定

以下为 Claude 在开发中必须严格遵守的附加命名协议：

✅ 所有模块必须归入标准目录结构

例如：

backend/
  ├── core/           # 业务逻辑核心模块，如 `xiao_zhi_client.py`
  ├── services/       # 音频/语音处理服务，如 `voice_service.py`
  ├── routers/        # API 路由，如 `voice_router.py`
  ├── utils/          # 工具函数，如 `audio_utils.py`
  ├── config/         # 配置相关，如 `env_loader.py`

✅ Claude 输出文件时必须说明文件名与路径

例如：

📄 文件名：tts_client.py
📁 路径：backend/core/tts_client.py

✅ 所有与小智协议相关的模块命名，需明确标识来源

例如：

功能	模块名建议	路径
与小智握手通信	xiaozhi_ws_client.py	backend/core/
小智音频监听模块	xiaozhi_listen_service.py	backend/services/
MCP 指令处理器	xiaozhi_mcp_handler.py	backend/core/


⸻

📦 示例

错误示例：

def GetUserVoice():
    ...

正确示例：

def get_user_voice():
    ...


⸻

🔁 持续更新机制
	•	本规范由用户和 ChatGPT 共同维护；
	•	每次增加新模块时，Claude 必须优先查阅本规范；
	•	如遇命名冲突、重复或含混，需提示用户确认，并主动建议命名优化方案；
	•	命名风格必须贯穿文档、代码、配置、日志、前端组件等所有维度。

⸻

