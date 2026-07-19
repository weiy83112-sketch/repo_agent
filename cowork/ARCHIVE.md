# Project Archive

## A-20260720-01 CLI Repo Agent 第一阶段完成

类型：milestone
状态：completed
日期：2026-07-20
关键词：CLI、LangGraph、Tool Calling、只读工具

摘要：
从 Python 包与命令行入口开始，完成了普通 Python Agent Loop，并将同一流程映射到 LangGraph。CLI 可以面向指定本地仓库回答问题，模型可调用 `list_files`、`read_file`、`search_text` 三个只读工具，工具结果和预期错误都会作为 Tool Message 返回 State。

关键知识：

- LangGraph 节点是接收最新 State 的函数；固定边控制顺序，条件边把路由返回值映射到下一节点。
- SDK 消息对象通过 `model_dump(exclude_none=True)` 转成可写入 State 的 Python 字典。
- `execute_tools` 闭包记住 `repo_path` 与可选回调，工具完成后固定回到模型节点。

验证结果：

- 完成路径边界、参数 schema、1 MiB 文件限制、20 图步骤与 60 秒模型超时。
- 作品集阶段提交：`623fd58`。

相关文件：

- `project/repo_agent/langgraph_agent.py`
- `project/repo_agent/tools/registry.py`
- `project/repo_agent/tools/file_tools.py`

再次检索条件：

- 讲解 LangGraph 图、Tool Message、闭包、异常链或修改现有 Agent Loop 时。

## A-20260720-02 固定评测集与可续跑 Runner 完成

类型：milestone
状态：completed
日期：2026-07-20
关键词：evaluation、Runner、Adapter、case_id、pytest、Django

摘要：
建立了 31 道固定代码问答题：Repo Agent 1 道、pytest 15 道、Django 15 道，并记录 pytest `67a174f...` 与 Django `3d34265...` 快照。实现 Pro/Flash 模型路由、统一 EvaluationAgent 接口、Baseline Adapter、逐题持久化和断点续跑。

关键知识：

- Ground Truth 保存标准文件与符号证据，不是模型自然语言答案范文。
- Adapter 隔离 Agent 实现，Runner 只调用统一 `agent.run()`。
- 单题异常成为评测结果；环境级异常停止整轮，已 `flush` 的结果仍可续跑。

验证结果：

- 31 个唯一 ID、固定提交、预期文件与符号全部通过离线校验。
- 17 个自动化测试通过；双轴审查除真实调用外无剩余问题。
- 框架提交：`443c20c`；真实 Flash/Pro 结果尚未生成。

相关文件：

- `project/evaluation/`
- `project/design/repo_agent/evaluation-runner-design.md`

再次检索条件：

- 继续 Baseline、实现 scorer、接入 Hybrid RAG Adapter 或分析断点结果时。

## A-20260720-03 Agent State 与 Python 数据结构学习

类型：knowledge
状态：completed
日期：2026-07-20
关键词：State、messages、列表、字典、TypedDict、reducer

摘要：
用户已掌握 `state` 是共享字典，`state["messages"]` 是消息列表，列表中的每项是包含 `role`、`content` 等键值对的字典。理解了 `append()` 修改原列表、`TypedDict` 描述字典形状，以及 LangGraph 中 `Annotated[list[dict], add]` 让节点返回的新消息追加到旧消息列表。

关键知识：

- `state["messages"].append({...})` 先从字典取出列表，再把一条消息字典追加到末尾。
- 节点输入 `state: AgentState` 是当前完整上下文；节点只返回本次增量，由 reducer 合并。
- 模型消息、工具结果和最终答案按时间顺序共同构成可继续推理的上下文。

验证结果：

- 已结合真实 `state.py`、普通 Agent Loop 和 LangGraph 调用链完成讲解与代码验证。

相关文件：

- `project/repo_agent/state.py`
- `project/repo_agent/agent.py`
- `project/repo_agent/langgraph_agent.py`

再次检索条件：

- 用户再次询问列表/字典、State reducer、消息追加或节点返回值时。

## A-20260720-04 环境变量与真实模型调用踩坑

类型：pitfall
状态：completed
日期：2026-07-20
关键词：dotenv、venv、402、API、数据外发

摘要：
`.env` 不会被 Python 自动读取，项目使用 `python-dotenv` 将变量加载到当前进程的 `os.environ`；修改 `.env` 后，新建 Router/重新启动进程才会读取新值。虚拟环境位于 `project/.venv`，必须在正确目录激活或使用完整解释器路径。无余额时 API 返回 402，请求变量不会被赋值，随后访问它会触发 `NameError`。

关键知识：

- `os` 是 Python 标准库模块，`os.environ` 是当前进程看到的环境变量映射，不是操作系统内核。
- API Key 缺失、余额不足、模型配置或连接失败是整轮环境问题，不应伪装成单题失败。
- 托管沙箱可能单独阻止将本地仓库片段发送到外部模型；用户授权与运行环境审批都必须满足。

验证结果：

- `python-dotenv` 已安装并由 `ModelRouter` 使用；密钥仍只在本地 `.env`。
- 真实评测首次尝试在网络外发审批处停止，没有生成有效题目结果。

相关文件：

- `project/repo_agent/model_router.py`
- `project/.env.example`
- `project/evaluation/README.md`

再次检索条件：

- 排查虚拟环境、Key 更新、402、模型连接或评测授权问题时。

## A-20260720-05 早期协作与项目状态说明已失效

类型：superseded-decision
状态：superseded
日期：2026-07-20
关键词：HANDOFF、TASKS、旧状态、mini-swe-agent

摘要：
早期 `cowork/HANDOFF.md` 把项目描述为“准备放置并阅读 mini-swe-agent”，根 README 也曾写成“只实现 complex、尚无自动化测试”。这些状态已被完整 CLI LangGraph Agent、双能力 ModelRouter、31 题评测框架和 17 个测试取代，不应再用于恢复当前进度。

关键知识：

- 恢复进度应先读取根 `AGENTS.md` 的当前断点，再按关键词搜索 Decisions/Archive，并与当前代码核对。
- 长完成清单和旧 handoff 不是长期决定；完成里程碑应压缩归档。

验证结果：

- 当前代码提交为 `443c20c`；`source/mini-swe-agent` 已用于早期学习，当前开发方向是 Baseline 后的 Hybrid RAG。

相关文件：

- `cowork/HANDOFF.md`
- `cowork/TASKS.md`
- `README.md`

再次检索条件：

- 旧文档与当前代码冲突，或准备删除旧上下文文件时。

## A-20260720-06 项目级上下文系统迁移完成

类型：milestone
状态：completed
日期：2026-07-20
关键词：AGENTS、DECISIONS、ARCHIVE、上下文迁移

摘要：
将分散在旧 Decisions、Tasks、Handoff、README 和设计文档中的上下文分类为当前断点、有效决定、历史知识和失效信息，建立根 `AGENTS.md`、精简的 Active Decisions 与可搜索 Archive。迁移只提炼结论，没有复制原始聊天；初次迁移保留旧文件，用户确认后删除了四份已被新系统取代的旧上下文文档。

关键知识：

- 当前状态只在 AGENTS 中替换；长期约束在 Decisions 合并；完成知识在 Archive 追加。
- 普通任务不读归档，历史相关任务先用关键词定位 1–3 个小节。

验证结果：

- 只修改三个目标文件；未触碰 Codex 设置、全局记忆或其他项目文件。
- 三份文件职责分离；已按用户确认删除 `cowork/HANDOFF.md`、`cowork/TASKS.md`、`cowork/README.md` 和 `cowork/WORKFLOW.md`。

相关文件：

- `AGENTS.md`
- `cowork/DECISIONS.md`
- `cowork/ARCHIVE.md`

再次检索条件：

- checkpoint、上下文过长、恢复旧教学或审查记忆分层时。
