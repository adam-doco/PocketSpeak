

🤖 Claude Prompt — V1.4 用户主页与设置页后端功能开发

🎯 本任务目标是为 PocketSpeak App 的底部菜单系统（学习页、我的页、设置页）提供后端接口支持，包含用户基础信息、学习统计数据、设置项接口等。

⸻

✅ 一、你的任务目标

你将负责实现以下接口，并确保符合 RESTful 规范，所有接口需基于 FastAPI 实现，并使用已有的用户身份认证机制。

⸻

📌 二、具体接口设计

1. 获取用户基础信息

GET /api/user/info

用途：返回用户头像、昵称、当前英语水平等级等基本资料

返回示例：

{
  "user_id": "u123456",
  "nickname": "Alex",
  "avatar_url": "https://cdn.pocketspeak.ai/avatar/123.jpg",
  "level": "B1",
  "level_label": "中级",
  "email": "alex@example.com"
}


⸻

2. 获取今日学习统计数据

GET /api/user/stats/today

用途：返回今日学习总时长（分钟）、自由对话次数、句子跟读次数等

返回示例：

{
  "date": "2025-09-29",
  "study_minutes": 42,
  "free_talk_count": 3,
  "sentence_repeat_count": 5
}

🔧 暂时使用 mock 数据，后续接入学习记录模块补全

⸻

3. 获取设置页面展示内容

GET /api/user/settings

用途：返回设置页面中可用的设置项配置（支持后期动态开关）

返回示例：

{
  "account_enabled": true,
  "show_terms": true,
  "show_privacy": true,
  "logout_enabled": true
}


⸻

4. 用户退出登录接口

POST /api/user/logout

用途：用于客户端退出登录，后端清理 token / session

返回：标准操作成功状态 { "success": true }

⸻

🧩 三、数据模型与存储说明

请创建或扩展以下模块：

模块	说明
models/user_model.py	定义 UserInfo, UserStats 数据结构
services/user_service.py	封装获取用户信息、统计数据的逻辑
routers/user_router.py	添加对应的 API 路由定义
schemas/user_schemas.py	使用 Pydantic 定义接口请求与返回模型


⸻

✅ 四、认证要求
	•	所有接口都必须使用现有 JWT Token 验证用户身份（参考 /api/user/me 实现方式）
	•	未登录状态下请求需返回 HTTP 401 Unauthorized

⸻

🧪 五、测试说明

请编写对应的测试文件 tests/test_user_dashboard.py，覆盖以下用例：
	•	获取用户信息（已登录 / 未登录）
	•	获取学习数据（Mock 返回）
	•	获取设置项内容
	•	正常退出登录

⸻

📁 六、目录结构建议

backend/
├── routers/
│   └── user_router.py
├── services/
│   └── user_service.py
├── models/
│   └── user_model.py
├── schemas/
│   └── user_schemas.py
├── tests/
│   └── test_user_dashboard.py


⸻

🧠 七、额外提示
	•	所有字段命名需符合 snake_case 与 Pydantic 规范
	•	用户等级（如 A1~C2）应包含可读名称（如 “入门”、“中级”）
	•	请确保接口注释完整、路径合理、命名统一

