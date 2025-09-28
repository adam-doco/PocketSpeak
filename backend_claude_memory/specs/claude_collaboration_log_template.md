

🧠 Claude 项目协作日志模板（增强版）

📌 适用范围：Claude 每次参与项目开发、文档撰写、模块搭建、重构优化等操作时，必须生成此日志，用于长期追踪任务演化与 Claude 记忆管理。

⸻

🗂 日志结构总览：

区块	内容简介
1. 任务概况	本次执行的基本信息，包括任务名、执行目标、产出类型等
2. 核心产出	所创建/修改的模块、文件、文档及其路径
3. 模块功能说明	每个模块/文件的功能定位、作用范围与逻辑细节
4. 与系统关系	本次任务对系统其他部分的影响/依赖/集成情况
5. 输入引用	所使用的项目参考资料、用户指令、历史文件等
6. Claude 思考过程	Claude 如何理解、拆解并实现本次任务的详细思路
7. 潜在问题	本次执行中遇到的边界情况、不确定点或可疑逻辑
8. 用户决策建议	需用户确认的点、建议推进的下一步操作
9. 结构索引锚点	本次任务新增的模块/文档应如何在系统中被引用或检索
10. 附件清单（可选）	所涉及的文件、截图、代码片段、数据样本清单等


⸻

📝 标准模板格式如下：

⸻

1. 📌 任务名称

Claude 完成的任务简述
如：构建语音识别模块 asr_manager.py，或撰写启动文档 getting_started.md

2. 🎯 执行目标

本次执行要解决的问题/要完成的模块/交付的目标
如：实现小智协议中的 listen 消息处理，接入麦克风流识别并将识别结果广播到前端状态管理器中

3. 📦 核心产出

文件/模块	类型	路径	新建/修改
asr_manager.py	模块	core/asr/	✅ 新建
main.py	启动器	/	✅ 修改
asr_protocol.md	协议文档	claude_memory/protocols/	✅ 新建

4. 🔍 模块功能说明（逐项）

对每个模块/文档，详细说明其功能、设计思路、关键方法
	•	asr_manager.py
	•	功能：连接小智 WebSocket，实现语音识别数据的实时接收、处理、回调
	•	方法：connect(), listen(), handle_binary()
	•	特点：支持二进制 OPUS 音频帧接入；可拓展情绪识别字段
	•	main.py
	•	修改内容：新增 --asr 启动参数，集成 ASR 模块入口
	•	影响范围：可能与 TTS 初始化流程共享依赖，应测试并发加载逻辑
	•	asr_protocol.md
	•	内容：详细描述小智 WebSocket 协议中的 listen 消息结构、header 格式、情绪字段说明

5. 🧬 与系统其他部分的关系
	•	新模块是否独立运行：asr_manager.py 可独立初始化，但依赖全局 config 和 ws client
	•	与现有模块的耦合：
	•	✅ tts_manager.py（共享 WebSocket 连接池）
	•	✅ state_manager.py（注册语音状态更新钩子）
	•	可能受影响的未来模块：
	•	❗ UI 前端消息展示组件需适配多情绪识别输出格式

6. 📖 所引用资料 / 上下文来源

来源	类型	路径
用户需求	任务指令	ChatGPT 对话 2025-09-25 16:11
协议参考	小智通信协议	claude_memory/protocols/xiaozhi_ws.md
历史代码	TTS 启动逻辑	core/tts/tts_manager.py

7. 🧠 Claude 的思考过程

详细描述 Claude 如何逐步理解任务、划分模块、设计接口、构建逻辑

	•	接收任务时，注意到 listen 消息使用二进制 OPUS 音频帧 → 需设置 Content-Type: application/octet-stream
	•	分析发现 TTS 与 ASR 都应通过同一 WebSocket 实例管理 → 抽象出 ws_manager 作为中介层
	•	设计 asr_manager.listen() 为异步生成器，支持持续数据流
	•	针对多情绪字段，增加 emotion 参数预留字段，便于未来拓展

8. ⚠️ 潜在问题与注意事项
	•	OPUS 解码目前未落地，仅透传至上层，未来需考虑集成 WebAssembly 解码器
	•	多并发 WebSocket 初始化时 config 读取不一致的问题需注意
	•	config 中尚未添加 enable_asr 字段，建议下次任务补充

9. 📌 结构索引锚点建议
	•	新模块路径：core/asr/asr_manager.py
	•	推荐在项目总结构索引文档中加入：

- 🔊 语音识别模块（ASR）: `core/asr/asr_manager.py`  
    - 功能：接入小智 listen 协议，实现实时语音识别流监听



10. 📎 附件清单（可选）
	•	示例音频包 sample.opus（测试用）
	•	listen 消息结构截图 listen_payload.png
	•	单元测试报告（未添加，建议后续任务补全）

⸻

📦 保存与命名规范
	•	所有协作日志必须存入 /claude_workspace/ 目录；
	•	文件命名统一为：

YYYYMMDD_任务描述.md

例如：

20250925_实现小智ASR模块并集成主流程.md



⸻

✅ Claude 使用规范
	•	执行每项任务后，Claude 必须完整填写本日志模板
	•	日志应作为 Claude 的“中期记忆载体”，以便后续多轮任务时参考回顾
	•	Claude 应主动提示用户确认并归档日志

⸻

