

📁 Claude 文件版本控制规则（File Versioning Rules）

🧠 文件位置：

请将本文件保存于以下路径中，以便 Claude 长期引用：

claude_memory/specs/file_versioning_rules.md


⸻

📌 文档目的

为确保 Claude 在有效记忆期内对项目的文件修改具备清晰追踪性与回溯能力，必须对所有代码和文档类文件建立统一的版本控制机制。

该规则适用于 Claude 生成和维护的所有以下类型文件：
	•	📄 Markdown 文档（如：规范、手册、协议）
	•	🧠 Claude 提示词（prompt）文档
	•	🧠 项目描述、PRD 文档
	•	🧱 Python / TypeScript / JavaScript / HTML 等代码文件

⸻

🗂️ 一、版本号命名规范

Claude 所有需长期维护的文件必须添加版本标记，格式如下：

vX.Y.Z

含义解释：
	•	X：重大结构调整（破坏性变更）
	•	Y：功能新增或重要模块加入
	•	Z：小改动、修复、措辞微调

✅ 示例：
	•	claude_workspace/pocketspeak_data_parser_v1.0.0.md
	•	claude_workspace/pocketspeak_ui_mockup_v0.3.2.md

⸻

✏️ 二、文件命名要求

统一采用以下命名规则：

[模块名称]_[功能或用途]_[版本号].md

模块名称为驼峰式或下划线连接，避免空格与中文，易于索引与归档。

✅ 示例：
	•	pocketspeak_tts_pipeline_v0.1.0.md
	•	claude_guidelines_memory_handling_v1.1.0.md

⸻

🔁 三、更新方式规范

每当 Claude 执行完任务并生成新版本内容，必须遵循以下步骤：

1. 拷贝原始版本，保留旧版本
	•	原始版本重命名为历史版本，例如：
xxx_v1.0.0.md → xxx_v1.0.0_backup.md

2. 创建新版本文件并命名为最新版本号
	•	新文件应命名为：xxx_v1.1.0.md

3. 在文档头部添加更新日志（Update Log）

格式如下：

## 📌 更新日志（Update Log）

- 日期：2025-09-25
- 变更者：Claude
- 变更说明：
  - 新增功能：添加用户配置项支持
  - 优化模块：重构语音输入逻辑
  - 修复问题：解决中文 TTS 输出乱码问题


⸻

📑 四、重大变更需额外记录说明文档

如出现以下情况，Claude 需生成独立说明文档，并另存于 claude_workspace/：
	•	更改系统架构或模块边界
	•	重命名重要文件/接口/类
	•	拆分/合并多个模块

说明文档命名方式：

[module]_refactor_notes_vX.Y.Z.md


⸻

✅ 五、用户确认机制（必须执行）

Claude 修改任何核心文件后，必须：
	1.	提示用户确认变更内容；
	2.	经用户确认后，才可将其标记为正式版本；
	3.	在 Claude 的日志系统中记录“此版本已获确认”状态。

⸻

🧠 六、搭配协作日志使用（强制）

所有文件版本更新记录，Claude 必须同步更新协作日志文件：

claude_workspace/project_work_log.md

在日志中描述：
	•	哪个文件被更新
	•	更新的版本号
	•	更新目的和可能影响
	•	与其他模块是否存在依赖/冲突

⸻

🧽 七、清理策略（可选）

为避免存储混乱，当项目超过 20 个版本时，Claude 可提示用户是否清理旧版本（如只保留最近 5 个主要版本 + 最初版本）。

⸻

📂 推荐目录结构

claude_workspace/
├── project_work_log.md
├── pocketspeak_data_parser_v1.0.0.md
├── pocketspeak_data_parser_v1.1.0.md
├── pocketspeak_data_parser_refactor_notes_v1.1.0.md
└── ...


⸻

⛔ 禁止行为
	•	不允许直接覆盖旧文件
	•	不允许无版本号的临时命名（如 final.md, latest.md）
	•	不允许更新后不写更新日志
	•	不允许非 Claude 协助用户私自修改文件（除非用户要求）

⸻
