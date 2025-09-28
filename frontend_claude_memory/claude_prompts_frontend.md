📌 技术栈：Flutter + PlatformView 嵌入原生层  
📂 模块所属目录：`frontend/`（Flutter 项目）

任务：实现 **启动绑定页面**（BindingPage）

功能目标：
- 启动时显示一个 6 位数字验证码，例如 “123456”
- 引导用户前往小智 AI 官网页面输入这个验证码以完成设备绑定
- 显示状态：等待绑定 / 绑定成功 / 绑定失败
- 若绑定成功，自动跳转至聊天页面

页面结构建议：
- 顶部标题：PocketSpeak / English Assistant  
- 中心验证码展示区域：数字样式大字号、可刷新按钮  
- 下方说明文字：“请在小智 AI 官网输入上方验证码绑定设备”  
- 状态提示栏：显示绑定状态  
- “重发验证码”或“重新获取”按钮（在绑定失败时可用）

交互逻辑：
1. 页面加载后调用 PlatformView 原生方法 `generateDeviceCode()` 返回 6 位码  
2. 显示码给用户  
3. 启动后台轮询原生层方法 `pollBindStatus()` 检查绑定结果  
4. 如果收到绑定成功信号，则跳转聊天界面  
5. 如果失败或超时，则显示错误并允许重试

必要前端 /平台方法接口：
- `PlatformBridge.generateDeviceCode()` → 返回 String 6 位数  
- `PlatformBridge.startBindPolling()` → 无返回，内部监听状态  
- `PlatformBridge.getBindStatus()` → 拉取当前状态（enum：pending / success / failed）

样式要求：
- 使用 Flutter Material 风格组件  
- 适配不同屏幕尺寸（手机 / 平板）  
- 使用 Column / Center / Padding 布局  

---

任务：实现 **聊天页面**（ChatPage）

你可以参考 Zoe 项目 Web 端的聊天界面布局（聊天气泡、语音按钮、历史记录） [oai_citation:1‡GitHub](https://github.com/adam-doco/Zoe)。

功能目标：
- 显示用户和 AI 的对话记录（文本 + 标识身份）  
- 支持用户点击麦克风按钮开始语音录制  
- 支持展示语音识别出的文本（中间状态）  
- 支持播放 AI 合成语音  
- 支持文字输入（备用输入方式）  
- 支持自动滚动到底部  

页面结构建议：
- AppBar 顶部显示角色头像 / 名称  
- 中间为 ListView 显示聊天条目  
- 聊天气泡包含文本 + 若有语音回复，显示语音播放按钮  
- 底部是行输入区域：文字输入框 + 麦克风按钮  

交互逻辑：
1. 用户点击麦克风按钮，则调用 `PlatformBridge.startListen()`  
2. 在录音过程中显示 “正在识别...” 文本  
3. 识别完成后，将文字追加到聊天记录中  
4. 调用后端通信模块（通过 PlatformView / 原生）发送录音流  
5. 接收到 AI 的回复音频 / 文本时，在聊天记录中追加，并播放音频  
6. 支持按播放按钮重放 AI 回复音频  
7. 若用户以文字输入，则调用 `PlatformBridge.sendText()` 接口获取回复  

接口方法建议：
- `PlatformBridge.startListen()`  
- `PlatformBridge.stopListen()`  
- `PlatformBridge.sendText(String text)`  
- `PlatformBridge.playTts(List<int> audioBytes)`  
- `PlatformBridge.getChatHistory()`  

样式要求：
- 聊天气泡区：左右对齐样式区分用户 / AI  
- 播放按钮：小图标按钮放在消息末尾  
- 自动滚动：每次插入新消息后滚动到底部  

---

⚠️ 注意事项（必须交给 Claude 严格遵守）：
- 所有 UI 必须用 Flutter Widget 实现，禁止使用 Web / HTML / JS 代码  
- PlatformView 嵌入的原生代码仅做通信与音频处理，不得写 UI 逻辑  
- 所有提示词必须包含界面结构、交互逻辑、接口方法、样式要求  
- 如果有参考 Web 端布局，需要 Claude 明确“参考 Web 端样式”但用 Flutter 实现  
- 每次任务结束须在 `frontend_claude_memory/` 下生成提示词文档（模块名_prompt.md）  