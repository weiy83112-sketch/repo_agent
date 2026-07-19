# Evaluation Runner Design

## 1. 目标

为当前 Repo Agent 建立一个可复现、可断点续跑、可复用的评测 Runner。Runner 先对当前文件工具版 LangGraph Agent 建立双模型 Baseline，后续在不改变核心评测逻辑的前提下接入 Hybrid RAG 或其他 Agent 实现。

本轮真实评测固定执行：

- `deepseek-v4-pro`，Thinking Enabled，`reasoning_effort=high`，31 道题；
- `deepseek-v4-flash`，Thinking Enabled，`reasoning_effort=high`，31 道题。

共 62 个 Agent 题目运行。单道题内部允许按照现有 LangGraph 流程进行多次模型和工具调用。

## 2. 设计原则

1. 固定题库、仓库快照、模型参数、最大图步骤和结果记录规则。
2. ModelRouter 隔离具体模型；评测代码只使用 `complex` 和 `simple` 能力。
3. Adapter 隔离不同 Agent 实现；Runner 只依赖统一的 `agent.run()` 接口。
4. Runner 的核心逐题执行逻辑不区分 Baseline、Hybrid RAG 或未来 Agent。
5. 每题完成后立即持久化，避免中断后重复产生模型费用。
6. 单题失败属于评测结果；整轮环境失效则停止运行。
7. `.env` 和真实 API Key 不得写入代码、结果、日志或 Git。

## 3. 目录结构

```text
project/evaluation/
├── __init__.py
├── __main__.py
├── schemas.py
├── loader.py
├── adapters.py
├── runner.py
├── scorer.py                         # 后续评分阶段创建
├── README.md
│
├── data/
│   ├── cases.jsonl
│   └── repositories.json
│
├── results/
│   ├── baseline-pro-high.jsonl
│   ├── baseline-flash-high.jsonl
│   ├── hybrid-rag-pro-high.jsonl     # 后续生成
│   └── hybrid-rag-flash-high.jsonl   # 后续生成
│
└── reports/
    ├── baseline-summary.md           # 后续生成
    └── hybrid-rag-comparison.md      # 后续生成
```

当前只创建本阶段实际使用的文件和目录。`scorer.py`、RAG 结果与报告在对应阶段再创建。

## 4. 固定数据

### 4.1 EvaluationCase

每道题增加稳定且唯一的 `case_id`：

```text
pytest-entry-001
django-call-003
repo-agent-call-001
```

题目字段为：

- `case_id`
- `repository`
- `question`
- `expected_files`
- `expected_symbols`
- `category`

`case_id` 不依赖 JSONL 行号。Loader 除现有字段校验外，还必须拒绝空 ID 和重复 ID。

### 4.2 Repository Snapshot

`data/repositories.json` 继续保存仓库名称、上游地址、固定 commit 和本地路径。Runner 启动前验证目标目录存在；pytest 与 Django 的 commit 必须与记录一致。

## 5. 模型路由

`ModelRouter` 提供两个能力方法：

```text
complex()
└── model=deepseek-v4-pro
    thinking={"type": "enabled"}
    reasoning_effort="high"

simple()
└── model=deepseek-v4-flash
    thinking={"type": "enabled"}
    reasoning_effort="high"
```

共享的客户端调用、60 秒超时和 SDK 异常转换放入私有实现，避免 `complex()` 与 `simple()` 重复。LangGraph 新增能力选择参数，但仍不接触具体模型名。

Router 同时提供当前能力的只读模型元数据，使结果记录可以保存准确模型、Thinking 模式和 Reasoning Effort，而无需在 Runner 中重复模型配置。

## 6. EvaluationAgent Interface 与 Adapter

Runner 依赖统一接口：

```python
agent.run(
    repo_path=repo_path,
    question=question,
    on_tool_call=on_tool_call,
)
```

本阶段实现 `BaselineAgentAdapter`。它在创建时保存 Router、能力名和最大图步骤，在 `run()` 内调用当前 `run_graph_agent()`。

未来 `HybridRagAgentAdapter` 可以额外保存 Retriever、Repository Index 和 Context Builder，但向 Runner 暴露的 `run()` 形状不变。

Adapter 不负责动态判断 Agent 类型。`__main__.py` 负责创建本轮使用的具体 Adapter，然后把对象传给 Runner。

## 7. Runner Interface

Runner 接收：

- 已校验的题目列表；
- 仓库名称到本地路径的映射；
- 一个满足 `EvaluationAgent` 接口的 Adapter；
- 本轮阶段名；
- 结果文件路径。

核心流程：

```text
加载已有结果中的 case_id
→ 按题库顺序遍历
→ 跳过已经持久化的 case_id
→ 选择对应仓库路径
→ 创建本题工具调用记录器
→ agent.run(...)
→ 记录回答、工具调用、耗时或单题错误
→ 立即追加一行 JSON 并 flush
```

Runner 不包含 `if baseline / if hybrid-rag`。阶段名只作为结果元数据和输出文件命名的一部分，不改变执行算法。

第一版按顺序运行，不并发。这样便于控制费用、日志顺序、断点状态和 API 限流风险。

## 8. EvaluationResult

每行结果至少保存：

- `case_id`
- `stage`
- `repository`
- `capability`
- `model`
- `thinking`
- `reasoning_effort`
- `answer`
- `tool_calls`
- `elapsed_seconds`
- `status`
- `error_type`
- `error_message`

成功时 `status="completed"`，错误字段为 `null`。单题失败时 `status="failed"`，`answer` 为 `null`。

结果中不保存 API Key、完整环境变量或 SDK 请求头。

## 9. 断点续跑

每题完成后立即写入并刷新文件。重新运行时先读取已有合法结果，建立 `completed_case_ids`，任何已经保存成功或单题失败结果的 ID 都跳过。

单题失败保留为 Baseline 成绩，默认不自动重试，避免只重试困难样本而改变评测规则。若需要重跑失败题，后续提供显式操作并保持旧结果可追溯，不在本阶段静默覆盖。

如果结果文件存在非法 JSON、重复 `case_id` 或与本轮模型配置冲突，Runner 在发送任何模型请求前停止。

## 10. 异常分级

### 10.1 工具层

路径、参数、编码和文件大小等预期工具异常继续沿用当前 LangGraph 行为：由 `execute_tools` 转成 `role="tool"` 错误消息，让模型有机会恢复。Runner 通常不会直接捕获这些异常。

### 10.2 单题 Agent 层

以下情况记录当前题失败并继续：

- `AgentTimeoutError`
- `AgentLimitError`
- 最终响应没有文本内容

为了正确分类，捕获时先处理 `AgentTimeoutError`，再处理它的父类 `AgentLimitError`。

### 10.3 整轮环境层

以下情况立即停止，不把剩余题目伪装成单题失败：

- API Key 无效或缺失；
- 余额不足；
- 模型不可用或请求配置非法；
- 题库或仓库快照不一致；
- 结果文件无法读取或写入；
- 用户中断。

停止前已经持久化的结果保留。环境修复后再次执行，Runner 从第一个未记录的 `case_id` 继续。

## 11. CLI 与运行顺序

`python -m evaluation` 负责装配 Router、Adapter、数据路径和输出路径。Runner 本身保持纯粹，不解析命令行。

正式运行顺序：

1. 离线校验题库、唯一 ID、仓库快照、结果路径和 Adapter；
2. 使用 Flash High 运行 31 题，输出 `baseline-flash-high.jsonl`；
3. 检查结果文件；
4. 使用 Pro High 运行 31 题，输出 `baseline-pro-high.jsonl`；
5. 检查两份文件的题目覆盖、错误和元数据。

真实模型运行已获得用户明确授权。实现或离线检查阶段不得提前发起未计划的额外模型请求。

## 12. 测试策略

付费调用前使用 Fake Adapter 验证：

- 题目按顺序交给 Adapter；
- 仓库映射正确；
- 工具调用回调被记录；
- 每题立即保存；
- 已保存 ID 会跳过；
- 单题错误继续；
- 全局配置错误在调用前停止；
- 两个能力生成不同且正确的结果文件名与模型元数据。

Fake Adapter 只返回固定字符串，不使用 DeepSeek Key。

## 13. 验收标准

- 31 道题拥有唯一 `case_id`，题库与仓库快照校验通过；
- Router 的 `complex` 与 `simple` 分别使用 Pro High 与 Flash High；
- Runner 不依赖具体 Agent 实现或具体模型名；
- Baseline Adapter 可以执行当前 LangGraph Agent；
- 中断后不会重复运行已保存题目；
- 单题失败与整轮环境失败按设计分级；
- 两份 Baseline 结果文件各覆盖 31 个唯一 `case_id`；
- 结果中不包含 API Key；
- 后续 Hybrid RAG 只需新增 Adapter 并选择新的输出阶段，不修改 Runner 核心循环。
