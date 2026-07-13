# Decision Log

This file records durable decisions that future agents should not rediscover from scratch.

## 0001 - Use `docs/` for teach-generated learning materials

Status: active

Teach-generated files are maintained under `docs/` instead of the repository root.

Reason:

- Keeps the project root clean.
- Separates learning material from future Agent code.
- Makes the learning system easy to browse from `docs/首页.html`.

## 0002 - Use Chinese filenames inside `docs/`

Status: active

Inside `docs/`, learning material paths use Chinese names:

- `课程/`
- `参考/`
- `学习记录/`
- `素材/`
- `首页.html`
- `学习目标.md`
- `学习资源.md`
- `教学笔记.md`

Reason:

- These files are for learning and review.
- Chinese names improve recognition and recall.
- HTML links have been updated to match these names.

Constraint:

- Future code folders should still use English filenames and directory names.
- `cowork/` keeps English filenames because it is an agent coordination folder.

## 0003 - DeepSeek-first model strategy

Status: active

The planned Agent project should default to DeepSeek V4 Pro for complex reasoning, with model routing abstractions for task categories such as `simple`, `complex`, and `planning`.

Reason:

- The user has enough DeepSeek quota.
- The project should not depend on Ollama as a cost-saving measure.
- A `ModelRouter` still keeps the workflow flexible if a future company requires local small models for simple tasks.

Constraint:

- Do not add local model complexity unless it becomes a concrete requirement.

## 0004 - Separate Agent workflow from model choice

Status: active

Agent workflow code should depend on capability names such as `simple`, `complex`, and `planning`, not concrete model names.

Reason:

- The Agent state machine should not change when the model behind `simple` changes.
- This makes it possible to replace DeepSeek Flash with a local small model later without rewriting Agent logic.

## 0005 - Put real project code under `project/`

Status: active

The runnable Agent project should live under:

```text
project/
```

Reason:

- Keeps root-level coordination simple: `docs/` for learning, `cowork/` for agent collaboration, `project/` for real code.
- Prevents future agents from mixing implementation files into `docs/`.
- Allows the code area to keep English paths while learning materials keep Chinese paths.

Constraint:

- Do not put runnable project source code directly in the repository root.
- Do not put project source code under `docs/` or `cowork/`.
- Use English directory names and filenames under `project/`.

## 0006 - Use `source/` for open-source Agent projects

Status: active

Open-source GitHub projects studied by the user should be placed under:

```text
source/
```

Reason:

- The user's original goal is to learn Agent development by reading real open-source Agent projects.
- `source/` keeps third-party projects separate from the user's own implementation under `project/`.
- Lessons in `docs/` should increasingly connect concepts back to concrete files under `source/`.

Learning loop:

```text
source/   read open-source Agent projects
docs/     record concepts and lessons
project/  implement the user's own Agent project
cowork/   coordinate agents and durable decisions
```

Constraint:

- Do not edit third-party source code casually unless the task explicitly requires an experiment or patch.
- Do not mix copied open-source project files into `project/`.

## 0007 - Store formal project design docs under `project/design/`

Status: active

Formal design documents for the user's own Agent project should be stored under:

```text
project/design/
```

Reason:

- Design docs are part of the user's real project, not only learning notes.
- Keeping them under `project/` anchors the implementation direction for future agents.
- Multiple AI agents can read and update the same project design context before writing code.
- `docs/` remains focused on learning material, lessons, references, and logs.

Naming convention:

```text
<short-english-topic>-design.md
```

Example:

```text
project/design/cli-repo-agent-design.md
```

Constraint:

- Use English filenames under `project/design/`.
- Do not add dates to the formal design document filename.
- Keep one active formal design document for the current project direction.
- Track step-by-step implementation tasks in `cowork/TASKS.md`, not in a separate implementation plan document.
- The document body may use Chinese as the main language, with important English terms preserved.
- Do not store formal project design docs under `docs/superpowers/specs/`.

## 0008 - Use manual-first teaching workflow

Status: active

The user wants to manually build the project from scratch while the agent teaches, guides, and verifies each step.

This includes:

- Downloading or cloning reference open-source projects into `source/`.
- Creating folders and files under `project/`.
- Copying or moving files when needed.
- Installing dependencies.
- Creating or activating virtual environments.
- Setting API keys or environment variables.
- Running setup, test, and CLI commands.
- Implementing the user's own project step by step.

Reason:

- The user's goal is to learn Agent development by doing the project manually, not by watching an agent silently generate everything.
- The user wants to understand Agent, LangChain, LangGraph, Agent protocol concepts, CLI, file operations, environment setup, and project workflow through the same project.
- Manual setup makes hidden project assumptions visible.
- It prevents agents from silently performing important operations that the user wants to understand.
- It reduces the risk of accidentally modifying or mixing third-party source code with the user's own project.

Agent responsibility:

- Read and maintain `cowork/TASKS.md` as the step-by-step teaching plan.
- Tell the user exactly what to do next through tasks.
- Explain the manual steps clearly.
- Prefer one small step at a time.
- Before introducing a new command-line option, library, Python syntax, Agent term, or framework concept, explain what it means in plain Chinese with a concrete example.
- Do not assume prior Python, CLI, package, or framework knowledge merely because a concept is considered basic. Re-teach prerequisite concepts when they are needed by the current Agent task.
- Before adding a new control-flow block or function call, show the execution order and use concrete example values to explain what each important variable contains.
- Break each new command into its executable, module or subcommand, option name, and option value before asking the user to run it.
- For code blocks that the user is expected to type manually, provide a teaching version with concise Chinese comments explaining every non-empty line. A comment may be placed on the preceding line when an inline comment would make the syntax harder to read.
- Keep the annotated teaching version in the project during the early learning stage. After the user understands and verifies the code, provide a clean version with only useful engineering comments when appropriate.
- Do not introduce unexplained syntax such as `--repo`, `argparse`, decorators, type annotations, or framework APIs inside a large code block.
- Explain each command before asking the user to run it.
- After the user finishes, inspect the workspace and verify the result.
- Only perform setup actions directly when the user explicitly asks the agent to do so.
- When a task introduces a new concept, explain it in context before moving on.

Constraint:

- Do not automatically download, clone, install, initialize, scaffold, or implement project assets unless the user explicitly requests agent execution.
- For `source/` projects, the default behavior is: user manually places the project under `source/`, then the agent reads and explains it.
- For `project/` implementation, the default behavior is: the agent explains what to create or type, the user performs the step, then the agent verifies and teaches from the result.
