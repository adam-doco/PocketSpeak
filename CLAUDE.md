

📘 CLAUDE.md — Claude 协作系统执行手册（总纲）

本文档是 Claude 协作系统的核心控制文档，包含 任务启动前的读取顺序、执行规范、文档路径说明、debug行为、版本控制、日志记录、命名结构 等内容。

❗ Claude 每次接收任务前必须完整阅读此文档，否则不得执行任务！

⸻

🧠 一、任务启动前的阅读顺序

Claude 在开始任何开发任务（撰写代码、文档、配置等）之前，必须遵循以下阅读路径：
	1.	项目蓝图
📄 backend_claude_memory/references/project_blueprint.md
了解 PocketSpeak 项目的总体目标、产品定位与版本规划。
	2.	开发大纲
📄 backend_claude_memory/specs/development_roadmap.md
熟悉开发流程、角色分工、Claude 的职责范围。
	3.	当前版本的 PRD
📄 backend_claude_memory/specs/pocketspeak_PRD_V1.0.md（如当前开发版本为 v1.0）
确认当前任务是否符合 PRD 中功能需求。
	4.	命名规范文档
📄 backend_claude_memory/specs/naming_convention.md
所有新建变量、模块、函数、文档、目录都必须遵守命名规范。
	5.	目录结构说明文档
📄 claude_memory/specs/folder_structure.md
所有新建或修改的文件必须存放在正确目录。
	6.	版本控制规则文档
📄 beckend_claude_memory/specs/file_versioning_rules.md
所有重要变更必须记录版本更新，并写入项目协作日志。
	7.	项目协作日志模板
📄 claude_memory/specs/worklog_template.md
完成每一个任务后，必须在 claude_workspace/ 下生成日志文档并归档。
	8.	前端/后端提示词文档（按任务类型读取）
📄 frontend_claude_memory/prompts/xxx_prompt.md
📄 backend_claude_memory/prompts/xxx_prompt.md
根据任务归属（前端 / 后端）读取提示词要求，避免偏差。

⸻

🧪 二、Claude Debug 行为规范

Claude 在调试（debug）代码时，必须遵守以下规则：
	1.	不得主观臆断
所有错误必须明确复现并定位，禁止凭“猜测”或“自以为是”擅自修改核心逻辑。
	2.	不得修改与当前问题无关模块
所有修改必须限定在问题模块内，若需跨模块改动，必须写入 工作日志 并征得用户同意。
	3.	避免遗忘上下文
Claude 应在每一次 Debug 前主动查看上一个调试日志，并明确记录调试目标、复现方式、尝试过的修复策略。

🔗 详细规则见：
📄 beckend_claude_memory/specs/claude_debug_rules.md

⸻

📝 三、Claude 工作日志规范

每一次 Claude 执行开发任务（不论成功与否），必须写入一份结构化日志：

📄 示例路径：claude_workspace/20250926_task_fix_audio_input.md
📄 模板参考：claude_memory/specs/worklog_template.md

日志应包括但不限于：
	•	执行目标
	•	修改内容及文件路径
	•	所引用的规则文档链接
	•	是否通过测试
	•	是否影响其他模块
	•	后续建议
	•	任务结果总结（必须详细说明任务是否完整完成，是否存在潜在风险）

⸻

💾 四、文档与目录约定（固定不变）

Claude 所有操作遵循以下目录结构：

📦 project-root/
├── claude_workspace/        # 所有Claude任务输出区（日志、临时代码等）
│   └── 20250926_fix_bug.md
│
├── claude_memory/           # Claude长期参考文档区（后端通用）
│   ├── specs/               # 所有规范性文件（命名、目录、调试规则等）
│   ├── protocols/           # 外部协议 / 通信协议等文档
│   └── references/          # 项目愿景、蓝图、品牌资料等
│
├── frontend_claude_memory/  # 前端 Claude 提示词专属目录  # 所有前端 Claude 任务提示词文档
│                
│
├── backend_claude_memory/   # 后端 Claude 提示词专属目录
│   └── prompts/             # 所有后端 Claude 任务提示词文档
│
├── pocketspeak/             # 项目主目录
│   ├── frontend/            # 前端 Flutter 项目 
│   └── backend/             # 后端 Python / FastAPI 项目

⸻

🛑 五、Claude 需严格遵守以下禁止项
	1.	❌ 不得擅自创建新目录、新命名结构
	2.	❌ 不得跳过日志记录
	3.	❌ 不得在未查阅 CLAUDE.md 的前提下执行任何任务
	4.	❌ 不得在 Debug 过程中同时进行多项修改
	5.	❌ 不得忽略版本号、修改时间等更新痕迹
	6.	❌ 不得自由发挥，无视提示词进行任意创作

⸻

✅ 六、执行完毕后的行为要求
	1.	🧾 必须在 claude_workspace/ 中生成工作日志
	2.	🧠 如果是新的功能模块，必须更新目录结构说明文档
	3.	🆕 如果是重要决策修改，必须提醒用户是否需要同步更新蓝图或PRD
	4.	🧹 如果编写测试代码，必须在测试后删除临时文件与测试数据

⸻

☎️ 七、沟通准则

Claude 在执行过程中如发现任何歧义、冲突、未知事项，必须第一时间向用户确认，不得自行判断继续执行。

⸻

📌 最后提示

🤖 Claude 是项目的执行引擎，而非创意源头。Claude 的任务是：准确执行用户的意图，最大程度减少错误、模糊与返工。


⸻

