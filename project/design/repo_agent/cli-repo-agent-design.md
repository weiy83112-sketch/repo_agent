# CLI Repo Agent Design

## 1. 背景

用户的目标不是复制开源 Agent 项目，而是：

```text
阅读 source/ 中的开源 Agent 项目
-> 学习 Agent 开发知识
-> 在 project/ 中从零实现自己的完整 Agent 项目
```

第一个参考项目选择 `mini-swe-agent`。它只作为参考教材，不作为用户项目代码来源。

第一版用户项目采用 CLI-first 路线，先做一个可在终端运行的本地仓库阅读 Agent。

## 2. 第一版目标

做一个 CLI 本地仓库阅读 Agent：

```text
用户在终端输入问题
-> Agent 读取目标仓库文件
-> Agent 调用工具获取真实信息
-> Agent 基于真实信息回答用户
```

第一版重点是完整跑通 Agent 核心链路，而不是做网页、数据库或自动写代码。

## 3. 非目标

第一版不做：

- Web 页面。
- 用户登录。
- 数据库。
- 自动修改代码。
- 自动执行危险命令。
- 多仓库管理。
- RAG 向量库。

这些能力可以在核心闭环稳定后再加。

## 4. 使用方式

预期命令：

```powershell
cd C:\Users\weiyun\Desktop\agent\project
python -m repo_agent --repo C:\Users\weiyun\Desktop\agent\source\mini-swe-agent
```

进入交互后：

```text
repo-agent> 帮我看看这个项目怎么启动
repo-agent> 这个项目的 Agent loop 在哪里
repo-agent> 解释 README 里的安装步骤
repo-agent> /exit
```

第一版 CLI 需要支持：

- 输入自然语言问题。
- 使用 `/exit` 退出。
- 打印 Agent 的最终回答。
- 在需要时显示正在调用的工具名，方便学习和调试。

## 5. 核心 Agent 流程

第一版 Agent loop：

```text
用户输入问题
-> 保存到 messages
-> 模型判断是否需要工具
-> 如果需要工具，输出 tool_call
-> 程序执行工具
-> 工具结果写回 messages
-> 模型继续判断
-> 信息足够后输出 final_answer
```

这个流程要对应前面课程中的概念：

- State
- messages
- Tool Registry
- Structured Output
- tool_call
- ToolMessage
- Conditional Edge

## 6. 第一版工具

只做安全读取类工具：

```text
list_files(path)
read_file(path)
search_text(query)
```

### list_files

用途：列出目标仓库某个目录下的文件和文件夹。

输入：

```text
path: string
```

输出：文件名列表。

### read_file

用途：读取目标仓库中的文本文件内容。

输入：

```text
path: string
```

输出：文件内容。

约束：只能读取 `--repo` 指定目录内部的文件。

### search_text

用途：在目标仓库中搜索关键词。

输入：

```text
query: string
```

输出：匹配文件、行号、片段。

## 7. 暂不开放的工具

第一版不做：

```text
run_command
write_file
edit_file
delete_file
```

原因：当前目标是读懂仓库，不是修改仓库。写入和命令执行会增加安全风险，也会分散学习主线。

## 8. 模型策略

默认生产模型方向：

```text
DeepSeek V4 Pro
```

Agent 代码不直接依赖具体模型名，而是通过 `ModelRouter` 暴露能力：

```text
simple
complex
planning
```

第一版可以先只实现最小可用的 `complex` 调用，但代码结构要保留后续扩展空间。

## 9. 目录设计

建议结构：

```text
project/
  design/
    cli-repo-agent-design.md
  repo_agent/
    __init__.py
    __main__.py
    cli.py
    agent.py
    state.py
    model_router.py
    tools/
      __init__.py
      registry.py
      file_tools.py
  tests/
    test_file_tools.py
    test_tool_registry.py
```

说明：

- `cli.py` 负责命令行输入输出。
- `agent.py` 负责 Agent loop。
- `state.py` 定义 State 和 messages。
- `model_router.py` 隔离模型选择。
- `tools/registry.py` 管理工具注册表。
- `tools/file_tools.py` 实现读取类工具。

## 10. 学习目标

做这个 CLI 项目时，用户需要顺带掌握：

- `cd`
- 当前目录 `cwd`
- 绝对路径和相对路径
- `python -m`
- 命令参数 `--repo`
- CLI 交互循环
- 环境变量，例如 `DEEPSEEK_API_KEY`
- `stdout` / `stderr`
- exit code
- Python 包结构
- 基础测试

这些知识不提前堆叠，遇到时逐个解释。

## 11. 验收标准

第一版完成时应满足：

- 可以从终端启动。
- 可以指定目标仓库路径。
- 可以连续输入问题。
- 可以退出。
- Agent 能调用 `list_files`、`read_file`、`search_text`。
- 工具调用结果能写回 messages。
- Agent 能基于真实文件内容回答。
- 工具只能访问目标仓库内部文件。
- 代码路径全英文。
- 用户能用自己的话讲清楚 Agent loop。

## 12. 后续扩展

第一版稳定后再考虑：

- Web 页面。
- 更完整的 LangGraph 状态机。
- RAG。
- Checkpoint。
- run_command 工具。
- write/edit 工具。
- 项目报告生成。
- 面试演示脚本。
