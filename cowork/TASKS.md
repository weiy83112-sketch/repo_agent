# Task Board

## Current

- Maintain Agent learning materials under `docs/`.
- Continue teaching Agent concepts using HTML lessons and reference pages.
- Current learning position: completed ModelRouter, Agent State, the ordinary Python Agent loop, and CLI integration; next is repeatable offline Agent-loop testing with a fake model router.
- Keep cowork decisions updated when path conventions, model strategy, or architecture changes.
- Keep future runnable Agent code under `project/` with English paths.
- Keep open-source projects under `source/`.
- Formal project design docs live under `project/design/`.
- First user project direction: CLI-first local repository reading Agent.
- Use manual-first teaching workflow: tasks tell the user what to do manually, then the agent verifies.

## Next Suggested Tasks

1. [Completed] Read `source/mini-swe-agent` README and core files with the user.
2. [Completed] Manually create the initial Python package skeleton under `project/repo_agent/`.
3. [Completed] Teach Python package structure, `__init__.py`, `__main__.py`, and `python -m repo_agent`.
4. [Completed] Manually add and verify the CLI interaction loop with `/exit`.
5. [Completed] Manually add and verify `--repo` parsing; learn `argparse`, `Path`, relative paths, and cwd.
6. [Completed] User manually creates the `tools` package and implements the first read-only tool: `list_files`.
7. [Completed] User manually connects `list_files` to the CLI through a temporary `/list` command.
8. [Completed] User manually implements and verifies a repository-confined `read_file` function.
9. [Completed] User manually connects and verifies `read_file` through `/read <relative-path>`.
10. [Completed] User adds and verifies `try/except` so expected read errors do not terminate the CLI loop.
11. [Completed] User understands the first `search_text` version; agent writes the missing saved copy, then verifies `.py` file path results.
12. [Completed] User extends `search_text` results with line numbers and matching text snippets; agent fixes and explains an indentation error.
13. [Completed] User connects `search_text` through `/search <query>`; agent fixes the branch indentation and verifies match, no-match, empty-query, and exit paths.
14. [Completed] User creates `project/.venv`; agent verifies Python 3.13.13 and pytest 9.1.1 are installed inside it.
15. [Deferred] User chose to verify tools manually against `source/` for now; automated file-tool tests can be added later.
16. [Completed] User moves CLI parsing and interaction from `__main__.py` into `cli.py` while preserving behavior.
17. [Completed] User creates `tools/registry.py` and learns how a tool name maps to a real Python function before adding model-driven tool calling.
18. [Completed] User enriches the registry with tool descriptions and parameter schemas so a model can understand when and how to call each tool.
19. [Completed] User builds a tool executor that combines the protected `repo_path` with model-provided arguments and dynamically calls the registered function.
20. [Completed] Agent completes and verifies runtime argument validation for object shape, required arguments, unexpected arguments, and string types; expected tool input errors now use `ValueError`.
21. [Completed] User understands the initial `ModelRouter` framework; agent creates and verifies `model_router.py` after the user approves the code.
22. [Completed] Connect the first DeepSeek-backed `complex` capability without hardcoding the API key or coupling Agent workflow code to a concrete model name; real paid requests remain deferred.
23. [Completed] Build and verify the ordinary Python Agent loop with tool calls, tool-result messages, final answers, and a maximum-step guard.
24. [Completed] Connect natural-language CLI input to `run_agent()` while preserving the manual `/list`, `/read`, `/search`, and `/exit` commands.
25. [Current] Build repeatable offline tests with a fake model router so the Agent loop can be verified without API balance.

## Current Task Detail

Goal:
Verify the complete Agent loop offline with deterministic fake model responses, without sending a paid DeepSeek request.

Manual action:
The agent first explains dependency injection, fake responses, and assertions. The user then builds the main test structure; the agent may complete repetitive fake response objects and narrow test setup.

Why:
The Agent loop should be testable even when the external model is unavailable, has insufficient balance, or produces nondeterministic output.

Verify:
Tests cover a direct final answer, one tool call followed by a final answer, a tool error returned to the model, and the maximum-step guard. No test performs a network request.

## Task Format

Each next task should be maintained in this style:

```text
Goal:
What the user is trying to learn/build.

Manual action:
The exact command, file, or folder the user should create/change.

Why:
The concept being learned.

Verify:
How the agent will check the result.
```

## Parking Lot

- Decide the final Python package name inside `project/`.
- Decide how DeepSeek API keys and environment variables will be stored safely.
- Decide whether `source/` projects should be cloned directly or stored as shallow copies.
