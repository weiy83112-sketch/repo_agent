# Agent Collaboration Workflow

## Roles

### GPT-5.5 / Codex

Use GPT-5.5 for work that benefits from stronger reasoning:

- Architecture decisions.
- Agent workflow design.
- Risky code changes.
- Debugging unclear failures.
- Reviewing DeepSeek-produced plans or code.
- Updating durable decisions in `cowork/DECISIONS.md`.

### DeepSeek V4 Pro

Use DeepSeek V4 Pro for work that benefits from more quota:

- Drafting explanations.
- Expanding documentation.
- Summarizing known concepts.
- Implementing clearly specified tasks.
- Maintaining routine HTML lessons after GPT-5.5 defines the structure.
- Producing first-pass code that GPT-5.5 can review.

## Collaboration Pattern

1. GPT-5.5 defines the goal, boundaries, and acceptance criteria.
2. DeepSeek performs the larger execution work.
3. DeepSeek records what it changed in `cowork/HANDOFF.md`.
4. GPT-5.5 reviews risky parts and updates `cowork/DECISIONS.md` when decisions change.

## Task Handoff Template

Use this format when handing work from one agent to another:

```md
## Handoff: <short task name>

### Goal
What should be achieved?

### Context
What has already happened?

### Files touched
- path/to/file

### Constraints
- Important rule 1
- Important rule 2

### Next step
The next concrete action.
```

## Model Usage Rule

Do not spend GPT-5.5 quota on bulk text expansion or routine formatting when the structure is already clear. Use GPT-5.5 where mistakes are expensive.
