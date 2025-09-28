# PocketSpeak v1.0 功能任务拆解说明

版本目标：  
构建基于“小智AI”语音通信协议的英语口语陪练应用 MVP，具备设备绑定、语音交互、文字输入与聊天记录显示能力。

---

## 📌 任务总览

| 编号 | 模块名 | 说明 | Claude 执行建议 |
|------|--------|------|-----------------|
| 1 | 设备生成器模块 | 复刻 py-xiaozhi 的硬件生成功能模拟设备并生成设备标识码 | 放入 `core/device_generator.py` |
| 2 | 验证码绑定模块 | 链接 WebSocket，获取验证码并提示用户绑定设备 | 放入 `services/bind_verification.py` |
| 3 | 绑定确认轮询模块 | 轮询等待小智AI返回 token 和 WebSocket URL | 放入 `services/bind_status_listener.py` |
| 4 | 语音通信模块 | 将用户语音转为 OPUS 后发送，接收 AI 返回结果并播放 | 拆为 3 步，放入 `services/voice_chat/` |
| 5 | 文字通信模块 | 使用 py-xiaozhi 的文字接口与小智 AI 对话 | 放入 `services/text_chat/text_client.py` |
| 6 | 聊天显示模块 | 前端网页 UI 显示对话消息与语音播放 | 前端代码放入 `frontend/` |
| 7 | 全局集成测试 | 打通所有模块流程，进行最终联调 | 放入 `main.py` 并记录到 `logs/` |

---

## 🧩 分任务详情

### ✅ 任务 1：设备生成器模块

- **目标**：生成唯一设备标识，用于 WebSocket 初始握手
- **来源**：py-xiaozhi 中的 `hardware_generator` 模块
- **输出**：JSON 文件保存 `device_id`, `device_name`, `timestamp` 等
- **存放位置**：`core/device_generator.py`

---

### ✅ 任务 2：验证码绑定模块

- **目标**：发送 `hello` 请求连接 WebSocket，监听 `verify` 类型消息中的 6 位验证码
- **UI行为**：将验证码打印至终端供用户前往官网输入
- **依赖**：任务1输出的设备信息
- **存放位置**：`services/bind_verification.py`

---

### ✅ 任务 3：绑定确认轮询模块

- **目标**：绑定后持续监听小智AI服务器，直到收到 `bind-status:success` 或 `mcp` 消息
- **输出**：获得 WebSocket URL 和绑定 token
- **存放位置**：`services/bind_status_listener.py`

---

### ✅ 任务 4：语音通信模块（3步）

1. **录音与发送模块**  
   - 采集麦克风语音 → 转为 OPUS → 封装为二进制 WebSocket 数据帧  
   - 放入 `services/voice_chat/speech_recorder.py`
2. **接收与解析模块**  
   - 监听 `mcp` 消息，提取文字结果  
   - 放入 `services/voice_chat/ai_response_parser.py`
3. **语音播放模块**  
   - 使用 TTS 播放返回语音（发送 `tts` 消息并播放收到的音频）  
   - 放入 `services/voice_chat/tts_player.py`

---

### ✅ 任务 5：文字通信模块

- **目标**：支持直接以文字发送输入内容并接收 AI 返回文字
- **接口**：调用 py-xiaozhi 中的文字客户端模块
- **用途**：调试或替代语音输入
- **存放位置**：`services/text_chat/text_client.py`

---

### ✅ 任务 6：聊天记录显示模块（前端）

- **功能**：实现 Web 聊天 UI，显示用户/AI气泡，语音播放按钮
- **建议参考**：Zoe 项目现有前端，或基于 `React + Tailwind` 重新开发
- **模块分布**：
  - `frontend/components/ChatBubble.jsx`
  - `frontend/pages/ChatRoom.jsx`
  - `frontend/utils/audioPlayer.ts`
- **播放支持**：可通过点击按钮播放小智 AI 的音频回复

---

### ✅ 任务 7：全局测试与联调

- **目标**：将所有模块打通，验证交互完整性
- **测试项**：
  - 验证码绑定是否成功
  - 是否能顺利发送语音 → 接收 → 播放
  - 文字输入流程是否能得到正确 AI 回复
  - 聊天界面是否正常渲染历史消息
- **入口**：`main.py`
- **日志**：将关键事件记录到 `logs/` 文件夹下，便于追踪问题

---

## 📁 推荐的项目结构

```bash
pocketspeak/
├── claude_memory/
│   └── specs/
│       └── pocketspeak_v1_task_list.md
├── core/
│   └── device_generator.py
├── services/
│   ├── bind_verification.py
│   ├── bind_status_listener.py
│   ├── text_chat/
│   │   └── text_client.py
│   └── voice_chat/
│       ├── speech_recorder.py
│       ├── ai_response_parser.py
│       └── tts_player.py
├── frontend/
│   └── ...（React 项目结构）
├── main.py
├── logs/
│   └── bind_log.txt / interaction_log.txt
└── requirements.txt

✅ 开发规范提示
	•	每个 Claude 模块执行前请使用统一提示词结构；
	•	每个执行完成的模块需生成记录放入 claude_workspace/;
	•	所有环境变量配置放入 .env 文件；
	•	所有模块应支持模块化导入，避免硬编码路径；