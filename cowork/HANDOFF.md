# Current Handoff

## Current State

The repository is currently a learning and planning workspace for an AI Agent development portfolio project.

Teach-generated learning materials have been moved under `docs/` and renamed with Chinese filenames:

```text
project/          # future runnable Agent project code, English paths only
  design/         # formal project design docs and implementation plans
source/           # open-source GitHub Agent projects for study
docs/
  首页.html
  学习目标.md
  学习资源.md
  教学笔记.md
  课程/
    0001-智能体状态机.html
    0002-浏览器F12调试入门.html
    0003-工具调用.html
    0004-工具注册表.html
    0005-结构化输出.html
    0006-Agent状态里的消息.html
  参考/
    智能体知识图谱.html
    智能体术语表.html
  学习记录/
    0001-模型路由理解.md
    0002-智能体状态机入门.md
    0003-工具调用入门.md
    0004-工具注册表入门.md
    0005-结构化输出入门.md
    0006-Agent状态消息入门.md
  素材/
    统一样式.css
  日志/
    2026-07-10-Agent学习日志.md
```

## Important Rules

- `docs/` may use Chinese filenames because it is for learning.
- Real Agent project code should be created under `project/`.
- Open-source GitHub projects for study should be placed under `source/`.
- Formal project design docs should be placed under `project/design/`.
- Paths under `project/` should use English names.
- Future project code should use English filenames and paths.
- `cowork/` uses English filenames because it coordinates agents.
- DeepSeek is the default model direction; do not introduce Ollama unless there is a concrete reason.
- Keep model choice behind `ModelRouter` capability methods such as `simple`, `complex`, and `planning`.
- Use manual-first teaching workflow: the agent tells the user what to do through `cowork/TASKS.md`, the user performs setup/build steps manually, then the agent verifies and explains.

## Last Completed Work

- Created teach workspace materials under `docs/`.
- Renamed teach folders and files to Chinese names.
- Taught and documented Agent state machine, browser F12 basics, tool calling, tool registry, structured output, and messages in Agent State.
- Rewrote lesson 0006 to explain messages through a concrete `source/` project-reading scenario.
- Created this `cowork/` coordination hub.
- Recorded that real project code belongs under `project/`.
- Recorded that open-source projects for study belong under `source/`.
- Recorded that formal project design docs belong under `project/design/`.
- Recorded the user's teaching preference: explain code line by line with minimal examples.
- Current project direction is CLI-first local repository reading Agent.
- Current workflow preference: user manually builds `project/` from scratch while the agent reads/maintains `TASKS.md`, explains each step, and verifies results.

## Suggested Next Step

Tell the user how to manually place `mini-swe-agent` under `source/mini-swe-agent`; after the user finishes, verify the folder and read the README together.
