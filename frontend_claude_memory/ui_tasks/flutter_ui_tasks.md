📱 PocketSpeak v1.0 - Flutter 前端功能开发任务拆分文档（含 Claude 提示词）

本文件用于指导 Claude 按照 Flutter + PlatformView 架构逐步完成 PocketSpeak v1.0 的前端功能开发任务。每个任务都包含：组件目标、接口对接要求、开发说明与 Claude 提示词。

⸻

✅ 项目技术栈说明
	•	前端框架：Flutter 3.x
	•	语音模块集成方式：PlatformView 嵌套 WebView（连接 py-xiaozhi 服务）
	•	页面结构：启动绑定页 + 聊天页
	•	对接后端：使用 HTTP 请求（FastAPI 后端）
	•	状态管理推荐：provider 或 riverpod

⸻

📄 页面结构拆解

1️⃣ 启动页（设备绑定页）

功能	描述
获取硬件ID	调用 py-xiaozhi 获取设备硬件ID（通过 WebView 传入）
获取验证码	调用后端 API 获取 6 位数字验证码，用于用户去小智官网绑定
显示二维码	将硬件 ID + 验证码渲染为二维码图片
后台轮询	每 3 秒调用一次接口检查是否完成小智 AI 绑定
跳转聊天页	绑定成功后，自动进入聊天页

🧠 Claude 提示词（启动页）

你正在开发 PocketSpeak v1.0 的 Flutter 前端页面，现在需要你编写启动页（设备绑定页）页面代码，要求如下：

1. 页面展示：
  - 上方展示当前硬件设备 ID（通过 WebView 拿到的值）
  - 中间展示一个大号 6 位数字验证码（从后端接口获取）
  - 下方展示绑定流程说明，例如“请访问小智官网输入上方验证码完成绑定”
  - 中间显示二维码图案（后端提供 QRCode 图片 URL）

2. 接口说明：
  - `GET /api/device-id`：获取硬件ID
  - `GET /api/get-verify-code`：获取验证码（返回：6位数字 + 绑定状态）
  - `GET /api/check-bind-status`：用于轮询绑定是否成功（返回：`true/false`）

3. 要求：
  - 每 3 秒自动调用 check-bind-status
  - 绑定成功后自动跳转到 ChatPage（使用 `Navigator.pushReplacement`）
  - 所有网络请求用 `http` 包实现，错误时需显示错误提示
  - 页面样式简洁居中，适配移动端尺寸


⸻

2️⃣ 聊天页（语音通信主界面）

功能	描述
语音录制按钮	点击后开始录音（调用 py-xiaozhi，或启动 WebView 控制）
显示用户语音识别内容	显示语音转文字后的内容
显示 AI 回复内容	展示 AI 回复文本内容
播放 AI 回复语音	接收语音 URL 并播放
聊天消息流	显示时间顺序的聊天记录（用户语音 + AI 回复）
滚动到底部	新消息进入后自动滚动页面到底部

🧠 Claude 提示词（聊天页）

你正在开发 PocketSpeak v1.0 的 Flutter 聊天页，要求如下：

1. 页面组成：
  - 顶部显示标题“PocketSpeak 聊天”
  - 中间为聊天记录列表（上下滑动，可展示用户语音与 AI 回复）
  - 底部为录音按钮（点击开始语音对话）

2. 聊天逻辑：
  - 点击录音按钮后，调用 WebView 中的 py-xiaozhi 服务开始录音
  - 录音完成后，py-xiaozhi 返回语音识别文本，并上传语音到后端
  - 后端返回 AI 回复文本 + 音频 URL（mp3）
  - 前端展示聊天记录，并播放回复语音

3. 所需接口：
  - `POST /api/send-audio`：上传语音并获取 AI 回复（返回：文字 + 音频URL）
  - `GET /api/audio/<file>`：音频播放 URL

4. 特别注意：
  - 使用 `WebView` 嵌入 py-xiaozhi 的页面组件，用 PlatformView 嵌套
  - 所有聊天记录需要使用 `ListView.builder` 实现，自动滚动到底部
  - 播放音频使用 `audioplayers` 或 `just_audio` 等主流音频包


⸻

