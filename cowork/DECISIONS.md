# Active Decisions

## D-001 项目目录与文档边界

状态：active
关键词：project、source、docs、路径
适用范围：所有代码、第三方源码、设计与教学资料

决定：
可运行代码和正式设计放在 `project/`，使用英文文件名；研究用第三方仓库放在 `source/`；教学资料放在 `docs/`，允许中文路径；协作上下文放在 `cowork/`。

原因：
把用户代码、第三方源码、学习材料和上下文分开，既方便工具处理，也避免误改或误提交本地资料。

执行要求：
- 不把可运行代码放入 `docs/`、`source/` 或 `cowork/`。
- 未经明确要求不修改 `source/` 中的第三方代码。
- 正式设计使用 `project/design/<topic>-design.md`；可按独立子系统保留多份有效设计。

## D-002 密钥与外部数据传输

状态：active
关键词：密钥、env、DeepSeek、数据外发
适用范围：模型调用、日志、结果、Git 与文档

决定：
真实凭据只从本地环境变量或被 Git 忽略的 `.env` 读取，任何源码、文档、结果和日志都不得保存密钥。向外部模型发送本地源码或产生付费调用前，必须说明发送范围并取得用户明确授权。

原因：
源码外发和凭据泄露是不同但都需要显式控制的风险；断点续跑也必须避免因环境错误继续消耗费用。

执行要求：
- `.env.example` 只能包含变量名和占位值。
- 不读取或打印真实 Key；若凭据进入代码、日志或 Git，应视为暴露并建议撤销。
- 评测结果不得保存 `.env`、环境变量、请求头或 API Key。

## D-003 模型路由与 Agent 实现隔离

状态：active
关键词：ModelRouter、capability、Adapter、模型隔离
适用范围：`project/repo_agent/` 与 `project/evaluation/`

决定：
Agent 工作流只依赖 `simple`、`complex` 等能力名，不接触具体模型。当前 `simple` 对应 DeepSeek Flash High，`complex` 对应 DeepSeek Pro High，均启用 Thinking；Evaluation Runner 只依赖统一 `agent.run()`，由 Adapter 隔离 Baseline 与未来 Hybrid RAG Agent。

原因：
模型或 Agent 实现变化时，不应重写 LangGraph 流程和评测循环。

执行要求：
- 具体模型名、参数和 SDK 调用集中在 `ModelRouter`。
- Runner 不添加 `if baseline / if hybrid-rag` 分支。
- 新 Agent 实现通过 Adapter 接入，并保持统一运行接口。

## D-004 手动优先的教学协作

状态：active
关键词：教学、manual-first、完整上下文、代码讲解
适用范围：教学、架构实现和用户操作

决定：
核心模块、主要控制流和架构接缝应先结合真实项目代码讲清，再由用户理解或操作；评测、测试、参数校验、重复代码和窄范围胶水可由 Agent 直接完成并汇报思路与结果，但必须标注并保留完整实现。

原因：
项目目标既是可运行作品集，也是用户的第一个 Agent 学习项目；只给孤立语句或静默生成全部代码都不利于掌握。

执行要求：
- 教学先展示调用者、被调用函数、关键变量、返回/抛出位置和后续路径。
- 讲解 RAG 或其他新技术时，先用一句端到端主流程作为全局地图，再拆解当前环节；后续细节持续回扣这条主流程。
- 每引入一项新技术，先展示它在端到端流程中的位置、上一步输入和下一步输出，再讲技术思路；默认不逐字段展开类型语法，生成代码时明确指出项目文件、类/函数位置及上下游连接点。
- 新语法、命令或框架 API 先用中文和具体值解释。
- 用户表示看懂并授权修改后，可直接落盘并验证；不得用 `...` 省略必要代码。
- 评测和测试默认由 Agent 实现与执行；除非它们直接影响 Agent 架构，否则不展开逐行教学。

## D-005 只读 Agent 的安全与可靠性边界

状态：active
关键词：只读工具、路径边界、文件限制、异常
适用范围：CLI Agent、LangGraph 和文件工具

决定：
当前 Agent 只允许列目录、读文件和搜索文本；仓库路径由程序控制，模型不能更换目标仓库。预期工具错误应转为 Tool Message 供模型恢复，框架或环境级错误通过项目异常隔离并由外层停止。

原因：
代码阅读不需要写入或执行权限；明确边界可降低路径逃逸、无限循环和难以诊断的框架耦合。

执行要求：
- 阻止仓库外路径，单文件上限 1 MiB。
- 单次图运行最多 20 步，模型客户端超时 60 秒。
- 未经新设计和用户批准，不增加写、删文件或执行系统命令工具。

## D-006 固定且可恢复的 Baseline 评测

状态：active
关键词：evaluation、baseline、case_id、断点续跑
适用范围：`project/evaluation/` 和模型评测

决定：
Hybrid RAG 实现前必须先使用固定的 31 道题和固定 pytest/Django 快照记录当前文件工具 Agent 的 Flash High、Pro High 两份 Baseline。Runner 顺序执行，每题完成立即写入并 `flush`，通过唯一 `case_id` 续跑。

原因：
固定题库、代码快照和模型配置，才能证明后续检索改造带来的真实提升，并避免中断后重复付费。

执行要求：
- 单题超时、步骤超限或无文本记录失败后继续；Key、余额、配置、快照和写入错误停止整轮。
- 已保存成功或失败题默认都跳过，不静默重试困难样本。
- 不改变 Runner 核心循环来适配 Hybrid RAG。

## D-007 Code-Aware Hybrid RAG 方向

状态：active
关键词：Hybrid RAG、AST、FTS5、Embedding、RRF
适用范围：Baseline 完成后的主要开发阶段

决定：
第一阶段面向约 1,000–10,000 个 Python 文件的仓库，采用 Python AST 切块、SQLite 持久化与 FTS5、本地多语言 Embedding、RRF 混合排序和 Context Builder；保留现有只读工具，并新增可追溯的代码检索能力。

原因：
精确标识符适合关键词检索，自然语言与英文代码匹配需要语义检索，AST 和上下文预算保证证据完整且可控。

执行要求：
- 先完成 Baseline，再依次实现领域模型、Scanner、Chunker、Index、Retriever 和 LangGraph 接入。
- 索引不得写入被分析仓库，更新必须事务化。
- 第一阶段不加入 Web、多 Agent、跨进程长期对话记忆或完整调用图。

## D-008 项目级上下文按需检索

状态：active
关键词：AGENTS、DECISIONS、ARCHIVE、checkpoint
适用范围：所有后续 Codex 任务

决定：
`AGENTS.md` 只保存自动启动所需的当前断点与高价值规则；`DECISIONS.md` 只保存仍有效决定；`ARCHIVE.md` 保存已完成里程碑、可复用知识、踩坑和失效决定。历史相关任务必须先搜索关键词，再读取少量命中小节。

原因：
把当前状态、长期约束与历史知识分层，可以减少上下文噪声，避免每次任务全文加载旧记录。

执行要求：
- 普通独立任务不读取 `cowork/`；教学先查 Decisions，恢复历史再查 Archive。
- 当前代码事实优先于归档；冲突顺序遵循用户要求、AGENTS、Decisions、Archive。
- 里程碑 checkpoint 时替换当前断点、合并决定并追加精简归档，不保存聊天原文。

## D-009 Agent 双向交接协议

状态：active
关键词：handoff、接手、交回、外部 Agent、dirty worktree
适用范围：任务交给其他 Agent、从其他 Agent 收回或跨任务继续时

决定：
项目只使用 `cowork/HANDOFF.md` 作为唯一活动交接单。`AGENTS.md` 保存启动与检索规则，HANDOFF 保存当前在途工作的负责人、代码状态、验证、授权边界、下一步和交回记录；接手和交回都在同一文件原位更新，不复制聊天或并行维护多份状态。

原因：
统一交接入口可以让不同 Agent 在 dirty worktree 中安全继续，并在交回时准确区分已完成、未验证、外部调用和仍需用户决定的事项。

执行要求：
- 接手前核对代码、Git 状态和运行进程；历史记录只按 HANDOFF 关键词定向检索。
- 交回时同步更新 HANDOFF 与 AGENTS 当前断点，里程碑和长期决定分别进入 Archive/Decisions。
- 交接不得扩大权限；付费调用、高资源任务、提交和 push 均沿用当前用户授权，暂停或撤回后必须重新取得授权。
