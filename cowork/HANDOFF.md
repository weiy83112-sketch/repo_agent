# Active Handoff

状态：cancelled
交接编号：H-20260722-01
当前负责人：primary agent
交回对象：项目所有者
最后更新：2026-07-22
关键词：Hybrid RAG、retrieval scorer、Embedding、batching、evaluation

## 交接目标

在不丢失当前未提交工作的前提下，继续完成 Hybrid RAG 的低资源离线检索评测，并在取得新的明确授权后才运行 DeepSeek 回答评测；最终生成 Baseline 与 Hybrid 对比报告并交回。

## 当前状态

- 已完成完整 RAG 问答链路、HybridRagAgentAdapter、`--stage baseline|hybrid-rag` 评测入口和断点结果隔离。
- 新增 `evaluation/retrieval_scorer.py`，用于 keyword、vector、hybrid 的 Recall@5/MRR；其 3 个专项测试通过。
- 因首次大型仓库向量化耗时过高，`RepositoryIndex` 已改为每批最多 256 个 CodeChunk 跨文件编码；相关 Index/Vector/Scorer 测试 19 个通过。
- 最近一次完整回归是在批处理改造前：94 个测试通过。批处理改造后尚未运行完整测试。
- 离线实跑两次被中止；两个高 CPU Python 进程及其启动进程已确认停止。
- 本轮没有启动 DeepSeek Hybrid 评测，没有新增付费模型结果。`hybrid-rag-flash-high.jsonl` 目前为空。

## 资源与中断事实

- 持久索引默认位于用户目录 `.repo_agent/indexes/`，不在被分析仓库中，也不应提交 Git。
- 首次运行中至少两个仓库索引已事务提交；最后一个大型仓库未完成。接手后必须检查实际索引状态，不依据文件大小猜测完成度。
- 原实现按文件调用 E5，20 分钟执行上限仍未完成；批处理优化已落盘但未完成真实大型仓库验证。
- 用户已因资源开销主动暂停任务。此前“离线完成后调用 DS”的授权不再有效；恢复本地高负载或任何付费调用前必须重新说明范围并取得明确授权。

## Git 与工作区

- 分支：`main`
- 当前提交：`f3c2db4` (`docs: add project context system`)
- 工作区包含从 Scorer 到完整 RAG 的大量未提交改动，均属于用户当前项目成果。
- 禁止 reset、checkout、clean、覆盖或删除现有改动；先运行 `git status --short` 并按文件核对。
- `source/pytest`、`source/django` 是固定只读快照，不得修改。

## 关键文件

- `project/repo_agent/retrieval/index.py`：SQLite、FTS5、向量保存与新批处理逻辑。
- `project/repo_agent/retrieval/retriever.py`：关键词、向量和 RRF 合并。
- `project/repo_agent/langgraph_agent.py`：retrieve_context 与模型调用链。
- `project/evaluation/adapters.py`：Baseline/Hybrid 统一接口与仓库运行时缓存。
- `project/evaluation/__main__.py`：双 stage 评测入口。
- `project/evaluation/retrieval_scorer.py`：尚未完成真实运行的离线检索评分器。
- `project/evaluation/scorer.py`：已有回答结果评分与 Markdown 报告。

## 接手步骤

1. 将本文件状态改为 `in-progress`，填写当前负责人和时间。
2. 阅读 `AGENTS.md`，再用关键词检索 `cowork/DECISIONS.md` 的 D-003、D-006、D-007、D-009；需要历史时只读取 Archive 对应小节。
3. 检查 Git 状态和是否存在遗留 Python 索引进程，当前代码事实优先。
4. 先运行不加载真实 E5 的完整 pytest；修复失败后再评估批处理正确性。
5. 提出比当前更低资源的验证方式和预计 CPU、内存、时间；未经用户重新授权，不恢复大型仓库全量向量化。
6. 不读取或输出 `.env`，不在日志、结果或交接单记录任何密钥。

## 建议下一步

优先验证批处理改造的完整回归，并测量单个小仓库的索引时间与峰值资源。随后考虑分批可提交、可续跑的 Embedding 回填，避免一个大型仓库在长事务中因中止而全部重算。方案获得用户确认后，再继续 Recall@5/MRR；检索达标且用户重新授权后，才运行 Flash/Pro 的 31 题 DeepSeek 评测。

## 交回要求

接手 Agent 完成或暂停时必须直接更新本文件，而不是另建交接文档：

- 状态改为 `returned`、`completed` 或 `blocked`，写明负责人和交回时间。
- 用精简列表记录实际修改文件、完成内容、执行命令和真实验证结果。
- 明确记录未完成事项、资源消耗、外部调用情况和是否仍需授权。
- 同步更新 `AGENTS.md` 当前断点；长期决定写入 `DECISIONS.md`，已完成里程碑写入 `ARCHIVE.md`。
- 不保存原始聊天、完整终端输出、密钥或可从代码直接读取的普通事实。
- 若产生提交，记录 commit；若未提交，明确保留的 dirty worktree 范围。未经用户要求不得自行 push。

## 交回记录

2026-07-22 用户取消外部 Agent 交接，工作由当前 Agent 继续。评测范围缩小为 pytest 的 15 道固定题，不再运行 Django 全量索引；本交接单保留作为未来双向交接模板。
