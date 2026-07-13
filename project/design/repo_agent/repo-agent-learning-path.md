# Repo Agent Learning Path

## 1. 文档定位

本文档只描述 `project/` 内 Repo Agent 从最小 CLI 到完整 Agent 的总体学习链路。

它不是第二份架构设计，也不是逐条实施任务：

```text
cli-repo-agent-design.md   定义项目要做什么以及整体设计边界
repo-agent-learning-path.md 定义通过项目依次掌握什么能力
```

具体的下一步操作仍由任务板逐项推进。

## 2. 最终目标

完成一个可以在终端中阅读本地代码仓库的 Agent：

```text
用户指定目标仓库
-> 用户提出自然语言问题
-> 模型判断需要哪些信息
-> 模型选择只读工具
-> 程序安全执行工具
-> 工具结果进入 Agent messages
-> 模型根据真实仓库内容继续分析
-> 信息足够后输出最终回答
```

用户最终应能独立讲清楚并实现：

- CLI 启动和参数解析。
- Python 包和模块拆分。
- 安全的文件工具。
- 工具注册表与工具 schema。
- 模型 Provider 与 ModelRouter。
- 结构化 Tool Calling。
- Agent State、messages 和 Agent loop。
- LangGraph 节点、边和条件边。
- 测试、安全边界与错误处理。

## 3. 阶段总览

```text
阶段 1  CLI 程序外壳
阶段 2  仓库范围与路径
阶段 3  安全只读工具
阶段 4  测试与代码模块化
阶段 5  工具注册表
阶段 6  模型接入与路由
阶段 7  结构化工具调用
阶段 8  普通 Python Agent loop
阶段 9  LangGraph 状态图
阶段 10 可靠性与作品集交付
```

## 4. 阶段 1：CLI 程序外壳

状态：已完成基础版本。

项目能力：

- `repo_agent` Python 包。
- `__main__.py` CLI 入口。
- `python -m repo_agent` 启动。
- 持续输入循环。
- `/exit` 退出命令。

学习重点：

- 当前工作目录。
- 包的父目录。
- `__init__.py` 与 `__main__.py`。
- `while`、`input`、`if`、`break`、`continue`。

## 5. 阶段 2：仓库范围与路径

状态：已完成基础版本。

项目能力：

- 使用 `--repo` 指定目标仓库。
- 将相对路径转换为绝对路径。
- 启动时验证仓库目录存在。

学习重点：

- `argparse`。
- 命令行 option 与 value。
- `Path`。
- 绝对路径和相对路径。
- Agent 的工作范围边界。

## 6. 阶段 3：安全只读工具

状态：已完成基础版本。

已经完成：

- `list_files`：列出仓库根目录内容。
- `read_file`：读取仓库内部文本文件。
- 路径越界检查。
- `/list` 与 `/read <relative-path>` 手动调用。
- `try/except` 处理预期读取错误。

已经完成：

- `search_text`：在 Python 文件中搜索关键词并返回文件路径、行号和匹配片段。
- `/search <query>`：在 CLI 中手动调用搜索工具，并限制显示前 20 条结果。

阶段完成标准：

- 三个工具都有清晰的输入和输出。
- 工具不能读取仓库外部文件。
- 工具错误不会导致 CLI 循环退出。
- 用户能解释每个工具函数中的数据流。

## 7. 阶段 4：测试与代码模块化

状态：进行中。

项目调整方向：

- 将 CLI 交互从 `__main__.py` 移到 `cli.py`。
- 保持 `__main__.py` 只负责启动。
- 为文件工具增加单元测试。
- 测试正常路径、不存在文件、目录误读和路径越界。

学习重点：

- 模块职责。
- 函数输入输出。
- `pytest` 基础。
- 正常测试和异常测试。
- 为什么测试是 Agent 工具安全边界的一部分。

## 8. 阶段 5：工具注册表

状态：未开始。

项目能力：

- 为每个工具定义名称、说明和参数结构。
- 通过工具名查找并执行真实 Python 函数。
- 将 CLI 中写死的工具判断逐步迁移到统一调度器。

目标结构：

```text
tool name
-> registry 查找
-> Python function
-> arguments
-> result
```

学习重点：

- Tool Registry。
- JSON Schema 或等价参数 schema。
- 函数本体和工具说明的区别。
- 结构化输入和动态调度。

## 9. 阶段 6：模型接入与路由

状态：未开始。

项目能力：

- 使用环境变量读取 API Key。
- 接入 DeepSeek 模型。
- 将模型调用封装在独立 Provider 中。
- 通过 `ModelRouter` 使用 `simple`、`complex`、`planning` 能力名。

学习重点：

- Model Provider。
- Model Router。
- 模型能力和具体模型名称解耦。
- API 请求、响应、超时和错误处理。
- 不在代码中写死密钥。

## 10. 阶段 7：结构化工具调用

状态：未开始。

项目能力：

- 将工具 schema 提供给模型。
- 让模型输出稳定的工具名和参数。
- 解析模型产生的 `tool_call`。
- 执行真实 Python 工具并得到观察结果。

核心链路：

```text
用户问题
-> 模型查看工具说明
-> 模型输出 tool_call
-> 程序解析 name 和 arguments
-> registry 找到真实函数
-> 函数执行
-> 返回 tool result
```

学习重点：

- Structured Output。
- Tool Calling。
- 模型只表达调用意图，程序负责真实执行。
- 参数校验和错误结果。

## 11. 阶段 8：普通 Python Agent Loop

状态：未开始。

先不用 LangGraph，亲手实现最小 Agent loop：

```text
用户问题
-> 写入 messages
-> 调用模型
-> 判断模型返回 tool_call 还是 final answer
-> 执行工具
-> 工具结果写回 messages
-> 再次调用模型
-> 直到得到最终回答
```

学习重点：

- Agent State。
- Human Message、AI Message、Tool Message。
- tool call id。
- 循环终止条件。
- 最大步骤数。
- 工具失败后如何让模型继续处理。

## 12. 阶段 9：迁移到 LangGraph

状态：未开始。

将已经理解的普通 Python Agent loop 映射成 LangGraph：

```text
State
Nodes
Edges
Conditional Edges
Graph compile
Graph invoke
```

建议节点：

- `call_model`：调用模型并追加 AI Message。
- `run_tool`：执行工具并追加 Tool Message。
- `should_continue`：判断继续调用工具还是结束。

学习重点：

- 状态如何在节点间传递。
- 条件边如何表达 Agent 的循环选择。
- LangGraph 解决了普通循环中的哪些工程问题。
- Agent 流程为什么不应绑定具体模型。

## 13. 阶段 10：可靠性与作品集交付

状态：未开始。

项目能力：

- 完整单元测试和 Agent 集成测试。
- 最大工具调用次数与超时。
- 文件大小限制和文本编码处理。
- 清晰的日志与工具调用展示。
- 配置示例和安全的环境变量说明。
- README、架构图、演示问题和面试讲解稿。

最终验收：

- 能指定任意本地目标仓库。
- 能根据自然语言问题自动选择只读工具。
- 能基于真实仓库内容回答。
- 工具访问被限制在目标仓库内。
- 单个工具错误不会导致 Agent 整体崩溃。
- 用户能从 CLI、工具、模型、messages、状态图五个层次讲清楚系统。

## 14. 当前所在位置

```text
阶段 4：测试与代码模块化
已完成：list_files、read_file、search_text、路径安全、手动 CLI 调用、基础错误处理
下一步：为三个文件工具建立测试
```

当前仍由用户输入 `/list` 和 `/read` 手动选择工具。这是为了先看清程序调用链。完成工具注册表和模型接入后，再由模型根据自然语言问题自动选择工具。
