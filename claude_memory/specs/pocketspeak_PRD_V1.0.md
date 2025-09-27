PocketSpeak V1.0 产品需求文档（PRD）

⸻

一、产品概述

PocketSpeak 是一款面向英语学习者的移动应用，旨在通过“小智AI”提供沉浸式语音交互体验，帮助用户练习口语、理解表达、提升交流能力。产品目标是打造“随时随地可对话的 AI 英语老师”。

本 PRD 文档聚焦于 V1.0 初始版本功能开发，实现基础语音聊天、用户绑定小智 AI 服务、对话可视化及语音播放等功能，为后续学习建议、内容分析与 Live2D 虚拟形象等模块打下基础。

⸻

二、目标平台与技术架构

支持平台：
	•	✅ iOS App（支持 App Store 上架）
	•	✅ Android App（支持 Google Play 上架）

技术栈与架构：
	•	前端框架：Flutter（跨平台）
	•	原生模块集成：使用 PlatformView 分别对接：
	•	🎙️ 原生麦克风录音与 OPUS 编码（小智 AI 语音识别所需）
	•	🧠 Live2D 虚拟角色渲染（后续版本支持）
	•	后端通信：
	•	✅ 使用 py-xiaozhi 项目作为语音通信核心中间层
	•	✅ 与小智 AI 服务端通过 WebSocket 协议连接，遵循其文档的 hello / listen / tts / mcp 数据格式规范

⸻

三、V1.0 版本核心功能

1. 小智 AI 激活与绑定流程
	•	首次启动时自动生成模拟硬件信息（DeviceId、CPU/显卡/内存等），符合小智服务要求（从 py-xiaozhi 中继承）
	•	提交绑定请求后展示 6位验证码，提示用户前往小智官网完成设备绑定
	•	App 后台启动绑定轮询任务，监听小智服务端发回的认证数据（完成设备注册）
	•	绑定成功后保存身份令牌，后续无需重复绑定

2. 实时语音对话（语音输入 → AI 语音输出）
	•	录音模块：集成原生麦克风模块，录音音频自动转换为 OPUS 格式（符合小智要求）
	•	对话交互流程：
	1.	用户按住按钮录音（或点击开始录音）
	2.	发送录音数据到 py-xiaozhi（会转发至小智 AI）
	3.	获取小智返回的语音回复（含二进制 OPUS 音频 + 对话文本）
	4.	播放语音回复 + 显示聊天文本

3. 聊天可视化（基础 UI 实现）
	•	显示用户语音输入转写内容（由 py-xiaozhi 处理返回）
	•	显示小智 AI 的回复文本与语音播放按钮
	•	可滑动的聊天记录视图

4. 音频播放模块（播放小智返回的 OPUS 音频）
	•	使用原生音频模块播放 OPUS 格式音频
	•	后续可扩展支持边下边播、缓存优化等

5. 错误处理与状态提示
	•	绑定失败提示（无法获取验证码 / 绑定超时）
	•	网络异常提示（WebSocket 断开 / 无法连接 py-xiaozhi）
	•	语音识别失败提示（空白识别 / AI 无响应）

⸻

四、开发原则与代码复用
	•	✅ 后端完全复用 py-xiaozhi，避免重复造轮子：
	•	✅ 绑定逻辑
	•	✅ WebSocket 协议对接
	•	✅ 音频收发与对话转写
	•	✅ 与小智 AI 的对接机制
	•	✅ 前端聚焦 UI 与平台集成，不做逻辑冗余

⸻

五、注意事项与关键实现点

OPUS 格式要求
	•	所有录音数据必须转换为 OPUS 格式编码（py-xiaozhi 文档已有详细流程）
	•	播放时也需解码 OPUS 格式

绑定流程两阶段逻辑
	•	A 路：首次绑定流程（获取验证码 → 官网绑定 → 监听返回数据）
	•	B 路：已绑定用户启动时直接加载 py-xiaozhi 获取身份令牌并连接小智

py-xiaozhi 使用方式
	•	推荐将 py-xiaozhi 封装为本地服务在 App 启动时自动运行
	•	Flutter 使用 MethodChannel 或 PlatformView 与本地服务通信

Live2D 支持（预留）
	•	当前 Flutter 无官方 Live2D SDK
	•	可通过 PlatformView 集成原生 Live2D 渲染模块（iOS 使用 Metal + Swift，Android 使用 OpenGL + Java/Kotlin）

⸻

六、后续版本展望（非 V1.0 内容）
	•	Live2D 虚拟角色展示与互动（支持嘴型动作、表情、肢体动画）
	•	AI 学习建议模块：分析用户与小智对话内容，推荐学习计划与反馈
	•	聊天记录分析、词汇复习、语音评分等辅助学习功能

⸻

七、文件结构建议（Flutter 项目）

pocketspeak_app/
├── lib/
│   ├── main.dart
│   ├── pages/
│   │   └── chat_page.dart
│   ├── widgets/
│   ├── services/
│   │   └── xiaozhi_service.dart
│   └── platform/
│       └── opus_recorder_view.dart
├── ios/
│   └── Runner/PlatformViews/Live2DRenderer.swift
├── android/
│   └── ... Live2DRenderer.java
├── assets/
│   └── icons, images, etc.
├── py-xiaozhi/   # 子模块 or 子进程封装
├── pubspec.yaml
└── README.md


⸻
