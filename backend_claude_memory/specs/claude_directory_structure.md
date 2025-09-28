
⸻

📘 Claude 协作目录结构说明（Claude Directory Structure Specification）

本说明文件用于明确 Claude 协作系统的目录结构设计原则、功能归属与协作规则，确保项目长期可维护、高效协作，尤其适配“代码小白”用户与多 AI 协作者。

⸻

🗂️ 目录结构总览

/claude_memory/                # Claude 的长期知识记忆与规则文档
│
├── specs/                    # 项目规范类文档（PRD、协作规则、流程手册等）
│   ├── naming_convention.md         # Claude 命名规范
│   ├── startup_guide_for_beginners.md # 项目启动指南（面向 0 基础用户）
│   ├── claude_directory_structure.md  # 当前文档：目录结构说明
│   └── ...（未来更多规范）          
│
├── protocols/                # 接入协议、平台通信、模型API说明等
│   └── xiaozhi_ws_protocol.md       # 小智AI通信协议说明
│
├── references/               # 项目背景、开发蓝图、愿景、参考材料
│   ├── project_blueprint.md        # PocketSpeak 项目蓝图
│   ├── dev_outline.md             # 开发任务总览（按阶段规划）
│   └── ...（如用户画像、竞品分析等）  
│
/claude_workspace/            # Claude 每次输出的任务结果（临时或阶段性产出）
│
├── [YYYYMMDD]_task-name.md   # 每次 Claude 任务产出命名规范
│   └── 示例：20250925_generate_prd_v1.md
│
├── README.md                 # 使用说明与操作规则


⸻

🧠 核心目录职责说明

目录路径	职责说明
claude_memory/	所有需长期记忆和持续引用的文档均存于此处。Claude 在每次任务中必须查阅相关文档确保上下文一致。
claude_memory/specs/	所有与 Claude 协作有关的“规范类文档”，包括命名规范、流程说明、PRD撰写规范等。此目录是 Claude 的“行为守则区”。
claude_memory/protocols/	存储项目所接入的通信协议（如 WebSocket、API接口说明、小智AI协议等）。供 Claude 在技术实现中查阅。
claude_memory/references/	作为知识资料库，记录产品设计愿景、开发蓝图、用户需求、竞品分析等内容，帮助 Claude 理解项目背景。
claude_workspace/	每次 Claude 执行任务的输出结果统一存放于此，便于归档与版本管理。仅保存实际产出，不保存 Claude 的中间推理或聊天记录。


⸻

📋 命名与管理规范（摘要）
	•	所有 Markdown 文件使用小写 + 下划线命名，英文描述清晰直观；
	•	所有任务产出使用：YYYYMMDD_任务简述.md 格式；
	•	Claude 在执行任务前必须查询 claude_memory/specs 下的规范文件，以免偏离开发标准；
	•	所有新增文档，Claude 必须在生成后说明其目录归属；
	•	禁止将代码、数据、资源文件等非文档内容放入此体系内；

⸻

🪄 示例任务流程回顾

操作	对应文件	所属目录
项目0基础启动指南	startup_guide_for_beginners.md	claude_memory/specs/
命名规范标准化	naming_convention.md	claude_memory/specs/
项目蓝图与目标梳理	project_blueprint.md	claude_memory/references/
小智AI通信协议文档	xiaozhi_ws_protocol.md	claude_memory/protocols/
PRD 产出任务记录	20250924_generate_prd_v1.md	claude_workspace/


⸻

📌 后续扩展建议
	•	增加 claude_memory/ai_roles/：用于定义 AI 助手角色（如 MOSS、口语教练、TTS服务协调员等）；
	•	增加 claude_memory/prompts/：存储 Claude 常用提示词模板，用于复用与标准化生成；
	•	每月或每阶段汇总产出结果，便于人类项目经理评估 Claude 工作质量；

⸻

如需引用本结构，请确保上下文明确、文档归类正确，Claude 执行任何新任务前必须先查阅此文档。

⸻
