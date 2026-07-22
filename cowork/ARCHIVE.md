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
- 框架提交：`443c20c`；Flash/Pro 两份真实结果各包含 31 个唯一 `case_id`。
- Flash 完成 26 题、`AgentLimitError` 5 题、252 次工具调用、总耗时 828.11 秒；Pro 完成 28 题、`AgentLimitError` 3 题、236 次工具调用、总耗时 1021.87 秒。
- 两个模型共同在 `pytest-call-002`、`pytest-related-001` 超限；结果文件未发现真实 Key 形态。

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
- 真实评测首次尝试在网络外发审批处停止；用户随后在本地 PowerShell 完成 Flash/Pro 各 31 道题，并由 Codex 离线核验结果。

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

## A-20260720-07 双模型 Baseline 自动评分完成

类型：milestone
状态：completed
日期：2026-07-20
关键词：Scorer、Baseline、证据覆盖、Flash、Pro

摘要：
实现独立于 Runner 和模型调用的确定性 Scorer，通过 `case_id` 对齐固定题目与结果，自动统计完成率、标准文件/符号覆盖、完整证据题数、工具调用、耗时、失败类型和分类指标，并生成 Flash/Pro 双模型 Markdown 摘要。人工正确性明确保留为未填写的 0/1/2 字段，不用字符串命中冒充正确性。

关键知识：

- 整体证据覆盖包含失败题，反映端到端可靠性；成功答案证据覆盖只观察已完成回答，避免混淆运行失败与答案证据不足。
- Flash 完成 26/31、Pro 完成 28/31；两者成功答案标准证据覆盖均约 97%，当前主要差距来自 `AgentLimitError`。

验证结果：

- Scorer 新增 7 个离线测试，项目完整测试共 24 个全部通过。
- 报告由本地 JSONL 生成，没有发起模型请求。

相关文件：

- `project/evaluation/scorer.py`
- `project/evaluation/schemas.py`
- `project/evaluation/reports/baseline-summary.md`
- `project/tests/test_evaluation_scorer.py`

再次检索条件：

- 比较 Hybrid RAG 与 Baseline、调整评分指标或进行人工正确性评分时。

## A-20260721-01 Hybrid RAG 本地 Embedding 环境就绪

类型：milestone
状态：completed
日期：2026-07-21
关键词：Hybrid RAG、multilingual-e5-small、Embedding、离线模型、CodeChunk

摘要：
为 Code-Aware Hybrid RAG 准备本地语义检索环境：项目虚拟环境已加入 `sentence-transformers==5.6.0`，`intfloat/multilingual-e5-small` 已下载到 Git 忽略的项目缓存目录。当前尚未实现 RAG 代码，开发断点停在领域模型设计，下一步创建并测试 `CodeChunk`、`RetrievedChunk`，再继续 Scanner、AST Chunker、Index 与 Embedder。

关键知识：
- 模型通过本地 Sentence Transformers 运行，不使用 DeepSeek 额度，也不向外部模型发送待分析仓库源码。
- Embedding 输出为 384 维向量；已验证模型能在离线模式加载并完成中英文问题与代码片段编码。
- 模型缓存位于 `project/.cache/huggingface/`，由根 `.gitignore` 排除，不应提交 Git。

验证结果：
- `multilingual-e5-small` 离线加载成功，测试向量形状为 `(2, 384)`。
- 示例问题与代码片段余弦相似度约为 `0.7820`。

相关文件：
- `project/requirements.txt`
- `.gitignore`
- `project/design/repo_agent/code-aware-hybrid-rag-design.md`

再次检索条件：
- 继续实现 `CodeChunk`、`RetrievedChunk`、Embedder、向量检索或排查本地模型缓存时。

## A-20260721-02 Hybrid RAG 领域模型完成

类型：milestone
状态：completed
日期：2026-07-21
关键词：CodeChunk、RetrievedChunk、领域模型、检索排名、不可变对象

摘要：
建立 `repo_agent.retrieval` 包并完成第一批 Hybrid RAG 领域模型。`CodeChunk` 只保存稳定、可追溯的代码事实，`RetrievedChunk` 通过组合 CodeChunk 保存某一次关键词、向量或混合检索产生的分数、来源和排名，避免把临时检索状态写回索引对象。

关键知识：
- 两个模型使用不可变 dataclass，保证进入索引或检索结果后不会被下游意外修改。
- Embedding 由 Repository Index 独立存储，不进入 CodeChunk，保持领域对象与具体向量存储实现解耦。
- 来源与排名保持一致：关键词或向量来源必须具有对应正整数排名，多来源结果不得重复标记。

验证结果：
- 新增领域模型测试 16 个全部通过。
- 项目完整测试共 40 个全部通过，未调用外部模型。

相关文件：
- `project/repo_agent/retrieval/__init__.py`
- `project/repo_agent/retrieval/models.py`
- `project/tests/test_retrieval_models.py`

再次检索条件：
- 实现 Scanner、AST Chunker、Repository Index、RRF，或调整 CodeChunk/检索结果边界时。

## A-20260721-03 Repository Scanner 与 AST Chunker 完成

类型：milestone
状态：completed
日期：2026-07-21
关键词：Repository Scanner、AST Chunker、file_hash、chunk_id、content_hash

摘要：
完成 Hybrid RAG 的文件发现和结构化切块层。Scanner 在仓库边界内筛选 Python 文件、裁剪常见缓存与构建目录，并生成相对路径、大小、修改时间和内容哈希；AST Chunker 将当前文件结构转换为 module、class、function、method CodeChunk，保存限定符号名、父符号、docstring 和准确行号。

关键知识：
- 当前增量粒度是文件级：file_hash 变化后重新解析整个文件；稳定 chunk_id 标识同一路径与符号，content_hash 单独反映代码正文变化。
- Chunker 支持同步/异步函数、嵌套类与嵌套函数，并将装饰器包含在符号源码范围内。
- 超大文件、无效 UTF-8、符号链接和读取错误会安全跳过并产生可见警告，不修改被分析仓库。

验证结果：
- Scanner、Chunker 与领域模型目标测试共 31 个通过；项目完整测试共 55 个通过。
- 对当前 `project/` 集成扫描得到 33 个 Python 文件、197 个 CodeChunk，197 个 chunk_id 全部唯一。

相关文件：
- `project/repo_agent/retrieval/scanner.py`
- `project/repo_agent/retrieval/chunker.py`
- `project/repo_agent/retrieval/models.py`
- `project/tests/test_repository_scanner.py`
- `project/tests/test_ast_chunker.py`

再次检索条件：
- 实现 Repository Index、增量替换、FTS5，或排查文件变化和代码块身份时。

## A-20260721-04 SQLite Repository Index 与 FTS5 完成

类型：milestone
状态：completed
日期：2026-07-21
关键词：SQLite、FTS5、增量索引、事务回滚、schema version

摘要：
完成 Repository Index 的 SQLite 持久化层：文件元数据、CodeChunk、预留 Embedding BLOB 和 FTS5 全文索引统一管理；索引使用仓库绝对路径哈希隔离并默认保存在被分析仓库之外。文件新增、修改、删除和未变化状态可被稳定识别，只有新增或修改文件重新 AST 切块。

关键知识：
- 一次增量更新统一事务提交；任一写入失败会回滚文件表、CodeChunk 和 FTS5，保留上一次完整索引。
- 修改文件会同步替换旧 CodeChunk 与 FTS5 项，删除文件会级联清理，AST 失败文件记录元数据但不保留陈旧搜索结果。
- FTS5 查询安全处理空白和标点，并在 BM25 排序前优先精确符号名，避免相似测试函数压过真实目标。

验证结果：
- Repository Index 专项测试 10 个通过，项目完整测试 65 个通过。
- 当前项目烟测首次索引 35 个 Python 文件、238 个 CodeChunk；第二次更新 35 个文件全部判定未变化，精确查询 `run_graph_agent` 排名第一。

相关文件：
- `project/repo_agent/retrieval/index.py`
- `project/repo_agent/retrieval/models.py`
- `project/tests/test_repository_index.py`

再次检索条件：
- 实现 Embedder、向量 BLOB、余弦检索、RRF，或排查增量事务与关键词排名时。

## A-20260721-05 Local Embedder 与向量检索完成

类型：milestone
状态：completed
日期：2026-07-21
关键词：multilingual-e5-small、Sentence Transformers、Embedding BLOB、余弦相似度、向量回填

摘要：
完成 Local Embedder 接口和 Sentence Transformers 实现，使用 E5 的 query/passage 输入边界将问题与带路径、符号、类型、docstring 的 CodeChunk 文本转换为归一化 float32 向量。Repository Index 可保存向量 BLOB、记录模型与维度配置、回填既有关键词索引并用 NumPy 矩阵执行余弦相似度排序。

关键知识：
- 新增或修改文件按文件批量向量化；未变化且已有向量的文件不会重复计算，旧关键词索引可在不重新 AST 的情况下补齐缺失向量。
- 单文件向量化失败保留 FTS5 关键词能力；模型名称或维度变化时明确要求重建，禁止在同一索引混用不兼容向量。
- 查询向量和存储向量统一归一化，因此矩阵点积就是余弦相似度；无向量时安全返回空结果。

验证结果：
- Embedder、向量 Index 与既有 Index 相关测试 21 个通过，项目完整测试 76 个通过。
- 本地模型在强制离线模式下输出 384 维向量；中文问题“在哪里创建模型客户端？”对两个示例代码块检索时将 `create_client` 排名第一。
- 全程未调用 DeepSeek，也未向外部服务发送仓库源码。

相关文件：
- `project/repo_agent/retrieval/embedder.py`
- `project/repo_agent/retrieval/index.py`
- `project/tests/test_embedder.py`
- `project/tests/test_vector_index.py`

再次检索条件：
- 实现 Hybrid Retriever、RRF、Context Builder，或排查本地模型、向量配置和语义排序时。

## A-20260722-01 Hybrid RAG 问答链路完成

类型：milestone
状态：completed
日期：2026-07-22
关键词：Hybrid Retriever、RRF、Context Builder、retrieve_context、ToolRuntime

摘要：
完成 Code-Aware Hybrid RAG 的问答主链。Hybrid Retriever 并行使用 FTS5 关键词结果和本地向量结果，经 RRF 合并、符号去重与单文件数量限制生成 RetrievedChunk；Context Builder 按预算整理带路径、符号、行号和来源的证据。LangGraph 在模型节点前只检索一次，将证据单独保存在 State，并在每次模型请求时临时组合证据与真实 messages，避免工具循环造成上下文重复。

关键知识：
- 固定 Baseline 继续使用原三种只读工具；RAG 图独立增加 `search_code` 和 ToolRuntime，不改变 Baseline 评测口径。
- CLI 启动时离线加载 E5、增量更新 SQLite 索引，再把 Retriever 和 Context Builder 注入 LangGraph。
- 向量查询失败时退化为关键词检索；证据不永久追加到 messages，但每轮模型调用都能读取同一份最新检索上下文。

验证结果：
- 混合检索、上下文预算、工具运行时、Baseline 隔离和 LangGraph 上下文循环均有确定性测试。
- 端到端测试真实经过 Scanner、AST Chunker、SQLite Index、Hybrid Retriever、Context Builder 和 LangGraph；项目完整测试 89 个全部通过。
- 验证过程未调用 DeepSeek，未向外部服务发送仓库源码。

相关文件：
- `project/repo_agent/retrieval/retriever.py`
- `project/repo_agent/retrieval/context_builder.py`
- `project/repo_agent/langgraph_agent.py`
- `project/repo_agent/cli.py`
- `project/repo_agent/tools/runtime.py`
- `project/tests/test_hybrid_rag_pipeline.py`

再次检索条件：
- 接入 Hybrid RAG Evaluation Adapter、比较 Baseline/RAG，或排查 RRF、证据预算与 State 注入时。

## A-20260722-02 Hybrid RAG 评测入口完成

类型：milestone
状态：completed
日期：2026-07-22
关键词：HybridRagAgentAdapter、Evaluation Runner、stage、索引复用、断点续跑

摘要：
新增与 Baseline 相同 `run(repo_path, question, on_tool_call)` 接口的 Hybrid RAG Adapter。Adapter 为每个仓库建立并缓存独立的 RepositoryIndex 与 HybridRetriever，同仓库题目复用运行时，结束时统一关闭 SQLite。评测命令新增 `--stage baseline|hybrid-rag`，输出到相互隔离的 JSONL 文件，现有 Runner 核心循环未修改。

关键知识：
- Adapter 缓存的是仓库路径到索引连接和 Retriever 的映射，不是把整个 SQLite 数据库长期复制到内存。
- Scanner、Chunker、Embedder 算法可以跨仓库复用；pytest、Django 等仓库使用独立索引，避免相对路径冲突、结果污染和增量删除干扰。
- `--validate-only` 只检查题库、仓库映射、元数据与断点文件，不建立索引、不发送模型请求。

验证结果：
- Hybrid Flash 的离线验证通过：31 道题、3 个仓库、0 个已保存 RAG 结果。
- Adapter 缓存、关闭、命令选择和输出隔离均有测试；项目完整测试 94 个全部通过。
- 验证过程未调用 DeepSeek。

相关文件：
- `project/evaluation/adapters.py`
- `project/evaluation/__main__.py`
- `project/evaluation/runner.py`
- `project/tests/test_evaluation_adapters.py`
- `project/tests/test_evaluation_cli.py`

再次检索条件：
- 实现 Recall@5/MRR、运行 Hybrid RAG 回答评测，或排查 Adapter 生命周期与断点文件时。

## A-20260722-03 Pytest Hybrid RAG 对比评测完成

类型：milestone
状态：completed
日期：2026-07-22
关键词：pytest、Recall@5、MRR、Hybrid RAG、Baseline 对比、DeepSeek

摘要：
将评测范围缩小为 pytest 的 15 道固定题，新增 `--repository pytest` 过滤和独立 `-pytest.jsonl` 结果文件。完成 keyword/vector/hybrid 离线检索评分，并真实运行 DeepSeek Flash、Pro 两组 Hybrid RAG 回答评测；随后从完整 Baseline 中筛选同一批 pytest 题，生成四组可复现对比报告。

关键知识：
- 离线 Recall@5：keyword 53.3%、vector 40.0%、hybrid 46.7%；Hybrid MRR 0.306 为三者最高，但前五命中仍需优化。
- 回答自动指标明显改善：Hybrid Flash 完成率 93.3%、证据覆盖 93.1%；Hybrid Pro 完成率与证据覆盖均为 100%。对应 Baseline Flash 为 73.3%/66.7%，Baseline Pro 为 80.0%/73.6%。
- 工具调用由 Baseline Flash/Pro 的 128/116 次下降到 Hybrid 的 95/91 次；自动证据覆盖不等于人工回答正确性。

验证结果：
- Hybrid Flash 14/15 完成、1 个 AgentLimitError；Hybrid Pro 15/15 完成。
- 仓库过滤、Scorer 过滤、结果文件隔离和检索评分均有测试；完整 pytest 99 个通过。
- 仅向 DeepSeek 发送已授权的 pytest 15 题两组请求，未运行 Django 或 repo_agent 回答评测。

相关文件：
- `project/evaluation/reports/retrieval-summary-pytest.md`
- `project/evaluation/reports/retrieval-details-pytest.jsonl`
- `project/evaluation/reports/baseline-vs-hybrid-pytest.md`
- `project/evaluation/results/hybrid-rag-flash-high-pytest.jsonl`
- `project/evaluation/results/hybrid-rag-pro-high-pytest.jsonl`

再次检索条件：
- 优化 Hybrid Retriever、分析 pytest 失败题、填写人工正确性或准备作品集评测结论时。
