# Cowork Coordination Hub

This folder coordinates work between two agents:

- GPT-5.5 / Codex: high-capability, low-quota agent.
- DeepSeek V4 Pro: higher-quota, lower-capability worker agent.

The goal is to preserve decisions, handoffs, task boundaries, and path conventions so both agents can work on the same project without losing context.

## Current Project Goal

Build an AI Agent development portfolio project while maintaining a durable learning system under `docs/`.

The current learning/project direction is:

- Python + LangGraph + LangChain.
- DeepSeek-first model strategy.
- Open-source project reading/maintenance Agent.
- Teach materials maintained under `docs/`.

## Path Convention

- `docs/`: Chinese filenames are allowed and preferred for learning materials.
- `source/`: open-source GitHub Agent projects studied by the user live here.
- `project/`: future runnable Agent project code lives here.
- Future code folders: use English filenames and directory names.
- `cowork/`: use English filenames for agent coordination stability.

This convention exists because Chinese filenames are helpful for reading learning material, but English paths are safer for code, scripts, tooling, and cross-agent execution. Third-party open-source code belongs in `source/`, while the user's own implementation belongs in `project/`.

## Key Files

- `WORKFLOW.md`: how GPT-5.5 and DeepSeek should divide work.
- `DECISIONS.md`: durable decisions and why they were made.
- `TASKS.md`: current and upcoming tasks.
- `HANDOFF.md`: current state for the next agent.
