# Task Board

## Current

- Maintain Agent learning materials under `docs/`.
- Continue teaching Agent concepts using HTML lessons and reference pages.
- Current learning position: completed ModelRouter, Agent State, the ordinary Python Agent loop, the LangGraph migration, and the LangGraph CLI connection; offline Agent-loop tests were skipped by user choice, and next is reliability work.
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
25. [Deferred] User chose to skip offline tests with a fake model router.
26. [Completed] Map the understood ordinary Python Agent loop to LangGraph State, nodes, edges, and conditional edges.
    - [Completed] Understand `TypedDict` as the Python schema that describes the existing State dictionary.
    - [Completed] Define `AgentState` and use the `add` reducer so node updates append new messages instead of replacing the existing list.
    - [Completed] Install `langgraph` in the project virtual environment and verify that `StateGraph` imports successfully.
    - [Completed] Create `langgraph_agent.py` and initialize `StateGraph(AgentState)` as `graph_builder`.
    - [Completed] Create `build_graph(router)` and the first `call_model` node; understand full-State input and partial-State output.
    - [Completed] Add the `START -> call_model` entry edge and understand how an edge controls execution order.
    - [Completed] Add `route_after_model` and conditional routing for tool calls versus final answers.
    - [Completed] Create the `execute_tools` node, execute every tool call in the latest assistant message, and return tool-result updates.
    - [Completed] Add the `execute_tools -> call_model` loop edge and complete the graph representation of the ordinary Agent loop.
    - [Completed] Compile the builder into a `CompiledStateGraph` and return the runnable graph from `build_graph()`.
    - [Completed] Understand the origin of `graph = graph_builder.compile()` and why `build_graph()` returns `CompiledStateGraph` even though it uses `StateGraph` internally.
    - [Completed] Add `run_graph_agent(repo_path, question, router)` to create initial State, invoke the compiled graph, and return the final assistant content.
    - [Completed] Connect the compiled LangGraph runner to the CLI while preserving `/list`, `/read`, `/search`, and `/exit`.
27. [Completed] Add an explicit `max_graph_steps=20` limit to each LangGraph invocation so repeated model/tool cycles cannot run forever.
28. [Completed] Translate `GraphRecursionError` into `AgentLimitError` and let the CLI continue after a step-limit failure.
29. [Completed] Distinguish the three timeout scopes and add a 60-second default timeout at DeepSeek client creation.
30. [Completed] Translate `APITimeoutError` into project-level `AgentTimeoutError`; the CLI catches its `AgentLimitError` parent and continues.
31. [Completed] Add a shared 1 MiB file-size limit: `read_file` raises `ValueError` for oversized files, while `search_text` skips them and continues searching.
32. [Completed] Understand how successful results and failure strings both become `role="tool"` messages in State, and how the graph edge triggers the model's second call.
33. [Completed] Pass an optional CLI callback through the runner into the graph; `execute_tools` now reports each selected tool before executing it.
34. [Completed] Create the repository-root portfolio `README.md`, pin the current runtime dependencies in `project/requirements.txt`, and explicitly ignore `.venv/`.
35. [Completed] Align the Git index with the portfolio boundary: keep the runnable project and public decisions, while retaining local teaching/reference/tool files only on disk.
36. [Completed] Review and stage the intended project changes as one coherent portfolio update before committing.
37. [Completed] Create the portfolio commit and push it to the existing GitHub `main` branch after final staged-diff confirmation.
38. [Completed] Design the final-version code-aware hybrid RAG upgrade for medium-to-large Python repositories.
39. [Completed] Review the written hybrid-RAG design before creating the implementation teaching plan.
40. [Completed] Understand why the evaluation baseline must be fixed before implementing RAG.
41. [Completed] Represent one Ground Truth evaluation case as a Python dictionary, then define its schema and JSONL storage format.
42. [Completed] Create the evaluation directory and the first manually verified code question.
43. [Completed] Load `cases.jsonl` one line at a time and validate each dictionary at runtime.
    - [Completed] Understand `cases: list[EvaluationCase]` and the normal list-building flow.
    - [Completed] Distinguish `path`, the opened `file` object, and each `raw_line` string.
    - [Completed] Understand `enumerate(file, start=1)` and `strip()`.
    - [Completed] Trace the blank-line and invalid-JSON error branches.
    - [Completed] Trace `validate_evaluation_case()` from object-shape checks through field validation and `cast`.
44. [Completed] Select two medium-to-large Python repositories and expand the dataset to about 30 questions.
    - [Completed] Select `pytest-dev/pytest` as the medium Python CLI/plugin benchmark.
    - [Completed] Select `django/django` as the larger multi-subsystem Python benchmark.
    - [Completed] Clone shallow snapshots under `source/` and record both exact commits in `project/evaluation/repositories.json`.
    - [Completed] Create 15 evidence-checked cases for each repository across all four categories.
    - [Completed] Review a representative pytest entry-point case so the benchmark is understandable without requiring full pytest or Django study.
45. [Current] Record the current Agent baseline without changing its retrieval behavior.
    - [Completed] Add stable, unique case IDs through the public loader interface.
    - [Completed] Move fixed input files under `evaluation/data/` and verify repository snapshots.
    - [Completed] Route `complex` to Pro High and `simple` to Flash High without leaking model names into LangGraph.
    - [Completed] Add the EvaluationAgent interface and Baseline Agent Adapter.
    - [Completed] Implement the generic, resumable Runner and result schema using a Fake Adapter first.
    - [Completed] Add the `python -m evaluation` assembly entry and complete offline checks (17 tests pass).
    - [Blocked] Run all 31 cases with Flash High, then all 31 cases with Pro High; the local sandbox requires renewed approval because source excerpts and questions are sent to DeepSeek.
    - [Pending] Verify both result files and publish the Baseline summary in the next scoring step.
46. [Pending] Define the code-index domain models: files, chunks, retrieval hits, and evidence.
47. [Pending] Implement and verify the repository scanner.
48. [Pending] Implement and verify AST-aware Python code chunking.
49. [Pending] Implement the transactional SQLite repository index and incremental updates.
50. [Pending] Implement the SQLite FTS5 keyword retriever.
51. [Pending] Add the local multilingual Embedder and vector retrieval.
52. [Pending] Combine keyword and vector rankings with Reciprocal Rank Fusion.
53. [Pending] Implement context deduplication, neighbor expansion, and budget control.
54. [Pending] Introduce ToolRuntime and register the `search_code` tool.
55. [Pending] Add the LangGraph `retrieve_context` node and preserve the existing tool loop.
56. [Pending] Run the fixed evaluation suite and publish the before/after portfolio report.

## Current Task Detail

Goal:
Record a reproducible baseline from the current file-tool Agent before adding code-aware retrieval.

Current substep:
Obtain renewed approval for the documented DeepSeek data transfer, then resume Flash from the first unsaved case.

Manual action:
Confirm that evaluation questions and source excerpts read by the Agent may be sent to DeepSeek. The API key, `.env`, and request headers are never included in model messages or result files.

Why:
The implementation and offline validation are complete, but the managed environment treats sending local repository content to an external model as a separate data-export decision.

Verify:
Both result files contain 31 unique case IDs with consistent model metadata and no secret values.

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
