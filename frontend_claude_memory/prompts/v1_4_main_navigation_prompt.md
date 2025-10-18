

🎯 Claude Prompt — V1.4 主页面与导航栏开发任务

🧠 背景说明：
PocketSpeak V1.4 版本旨在实现登录后主界面的基本框架，包括底部导航栏、学习页、我的页、设置页四大结构。你将负责使用 Flutter 构建前端页面，结构清晰、样式现代，并为未来扩展预留能力。

⸻

✅ 你的任务目标

请使用 Flutter 编写以下页面结构，并确保组件之间结构清晰，便于扩展与维护：

🧱 1. 底部导航栏（全局）
	•	使用 BottomNavigationBar 实现底部导航栏
	•	默认包含两个页面：
	•	学习页（label: “学习”，icon: 📘）
	•	我的页（label: “我的”，icon: 🙋）
	•	要求支持未来可插入 3~5 个页面，使用动态项（如 List<BottomNavigationBarItem>）
	•	每个 Tab 使用 PageView 或 IndexedStack 管理状态，避免切换重绘

⸻

📘 2. 学习页面 /learning
	•	页面顶部显示一行当前英语水平，例如：“当前等级：B1 中级”
	•	数据通过 UserProvider 或 UserService.getUserInfo() 获取
	•	下方是三个功能按钮区域，要求卡片风格：

按钮	路由	图标建议
自由对话	/chat	💬
句子跟读	/sentence	🗣️
学习历史	/history	📜

	•	每个按钮独立封装为 LearningActionCard 组件，支持传入 icon / label / callback

⸻

🙋 3. 我的页面 /profile
	•	展示以下信息：
	•	用户头像（使用网络头像或默认头像）
	•	昵称（从用户信息读取）
	•	今日学习时长（从后端接口 /api/user/stats/today 获取，暂用 mock）
	•	页面底部有一个“设置”按钮，跳转至 /settings

⸻

⚙️ 4. 设置页面 /settings
	•	包含以下四项功能项，每项为一个 ListTile（或卡片样式）：

名称	描述	路由/操作
账号管理	修改邮箱 / 绑定账号（后续实现）	/settings/account
用户协议	展示 app 协议文档	/settings/terms
隐私政策	展示隐私政策文档	/settings/privacy
退出登录	清除 token 并返回登录页	清空本地数据并跳转


⸻

🧩 数据获取与接口说明
	•	所有用户数据应通过 UserService 获取：
	•	UserService.getUserInfo()
	•	UserService.getStudyStats()

请创建或扩展以下类：
	•	user_model.dart：用户数据模型
	•	user_service.dart：负责从后端拉取用户信息与学习数据
	•	auth_provider.dart：管理当前登录状态（参考已有登录逻辑）

⸻

🎨 设计要求
	•	风格参考 Zoe 项目 UI 示例，保持现代 / 简洁 / 明亮风格
	•	所有按钮需带 icon + label
	•	卡片组件封装良好，代码结构清晰，命名规范

⸻

📁 目录建议

lib/
├── pages/
│   ├── learning_page.dart
│   ├── profile_page.dart
│   ├── settings_page.dart
├── components/
│   ├── bottom_nav.dart
│   ├── learning_action_card.dart
├── services/
│   └── user_service.dart
├── models/
│   └── user_model.dart
├── providers/
│   └── auth_provider.dart


⸻

📌 最终验收标准
	1.	底部导航栏正常切换，支持扩展
	2.	学习页显示用户等级 + 3 个功能按钮
	3.	我的页展示头像 / 昵称 / 今日学习时长 + 设置按钮
	4.	设置页 4 个功能项能正确跳转或执行
	5.	所有页面结构模块化、样式统一、代码清晰

