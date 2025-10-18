收到，我们将 v1.3 的目标聚焦为「构建完整的用户账户系统」，这是一个关键性框架功能。以下是为 PocketSpeak V1.3：用户登录与注册系统 撰写的完整 PRD（产品需求文档），格式清晰、内容详尽，Claude 可直接执行。

⸻

📘 PocketSpeak V1.3 — 用户登录与注册功能 PRD

版本目标：
✅ 构建用户账户系统，实现 App 启动时的登录/注册功能
✅ 支持邮箱验证码登录（基础功能）
✅ 支持 Apple ID 登录（高级功能）
✅ 构建完整的用户信息模型，与 V1.2 用户英语等级记录等数据打通
✅ 为后续添加“手机验证码登录”、“微信/Google登录”等多登录方式做架构预留

⸻

🧠 1. 功能概述

功能模块	描述
启动页判断登录状态	判断是否已有有效用户凭证，无则跳转登录页
登录/注册界面	用户输入邮箱 + 验证码进行登录/注册，或使用 Apple ID 登录
邮箱验证码发送接口	通过后端接口请求发送邮箱验证码，后端预留对接邮件服务商
用户数据存储模型	构建统一用户数据结构，支持用户 ID、邮箱、登录时间、英语等级等扩展字段
本地登录状态存储	登录成功后持久化 Token，用于自动登录与用户态持久化


⸻

📱 2. 页面设计（Flutter）

2.1 App启动判断逻辑（Splash 或 Wrapper）
	•	判断是否存在有效的本地 auth_token
	•	若无 → 跳转到 LoginPage
	•	若有 → 请求 /api/user/me 校验有效性并跳转首页

⸻

2.2 LoginPage 登录/注册页

元素	描述
欢迎标题	欢迎使用 PocketSpeak
邮箱输入框	输入邮箱（格式校验）
发送验证码按钮	请求验证码（防重发计时器）
验证码输入框	6位数字验证码
登录 / 注册按钮	发送请求并获取 Token
Apple 登录按钮	使用 Apple ID 登录
登录后提示	登录即代表同意服务条款与隐私政策


⸻

2.3 登录成功逻辑
	•	保存 auth_token 到本地
	•	请求 /api/user/me 获取用户信息（包括是否已有 level 信息）
	•	跳转至主界面（若无 level 信息，跳转到 V1.2 的测评页）

⸻

🧩 3. 用户模型设计

{
  "user_id": "uuid",
  "email": "user@example.com",
  "email_verified": true,
  "login_type": "email_code", // 或 apple
  "apple_id": "apple-user-id", // 可选
  "english_level": "B1", // 来自 V1.2
  "created_at": "2025-10-01T00:00:00Z",
  "last_login_at": "2025-10-01T12:00:00Z"
}

后端模型需使用 Pydantic 定义，并保存在数据库中（未来可接MongoDB或PostgreSQL）

⸻

🔧 4. 后端接口设计（FastAPI）

4.1 发送验证码
	•	POST /api/auth/send-code

{
  "email": "user@example.com"
}

	•	响应：

{ "success": true }

✅ 后端应支持验证码有效期（如5分钟）与冷却机制（如60秒内不可重复发送）
✅ 使用可插拔的邮件发送模块（如 SMTP / Mailgun / Sendgrid）

⸻

4.2 邮箱验证码登录
	•	POST /api/auth/login-code

{
  "email": "user@example.com",
  "code": "123456"
}

	•	成功响应：

{
  "token": "jwt_or_custom_token",
  "user": {
    "user_id": "...",
    "email": "user@example.com",
    "english_level": "B1"
  }
}


⸻

4.3 Apple 登录（预留接口）
	•	POST /api/auth/login-apple

{
  "apple_id_token": "xxx"
}

✅ 后端需验证 Apple ID Token 并绑定用户 ID
✅ 若首次使用 Apple 登录，应创建新用户记录

⸻

4.4 获取当前用户信息
	•	GET /api/user/me

Headers: Authorization: Bearer <token>

返回当前登录用户所有基础信息。

⸻

🔐 5. 登录状态管理（前端）
	•	登录成功后将 token 存储至本地（如 SharedPreferences / SecureStorage）
	•	后续所有请求需自动附带 Authorization: Bearer <token> 头
	•	启动时调用 /api/user/me 验证是否有效 → 决定是否跳转 LoginPage

⸻

🧱 6. 数据存储说明

数据	存储位置	说明
登录 Token	本地安全存储	用于持久登录
用户基础信息	后端数据库（如 Mongo）	与 email、level 等绑定
验证码记录	后端缓存系统（如 Redis）	验证码 + 过期时间 + 冷却限制


⸻

🔁 7. 流程图

App 启动
 └─► 检查 token 是否存在
     ├─ 有 → 验证有效性 → 跳主界面
     └─ 无 → 跳 LoginPage
           ├─ 邮箱登录
           │   ├─ 输入邮箱 → 请求验证码
           │   └─ 输入验证码 → 登录成功
           └─ Apple 登录 → 登录成功
→ 保存 Token → 获取用户信息 → 判断是否需测评 → 进入主界面


⸻

📂 8. 目录结构建议

前端 Flutter

frontend/lib/pages/auth/
├── login_page.dart
├── email_input.dart
├── code_input.dart
└── apple_login_button.dart

后端 FastAPI

backend/routers/auth.py
backend/services/auth_service.py
backend/models/user.py
backend/utils/email_service.py  # 可对接 SMTP / Sendgrid


⸻

✅ 9. 验收标准
	•	用户可通过邮箱 + 验证码完成登录
	•	验证码机制可防刷、防重发，带有效期
	•	登录成功后自动拉取用户信息并存储
	•	用户信息模型中包含英语等级字段
	•	Apple 登录功能可正常调用（预留）
	•	支持 token 持久化登录，App 重启仍保持登录状态

⸻