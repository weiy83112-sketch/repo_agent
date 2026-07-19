from pathlib import Path
from types import SimpleNamespace

import evaluation.adapters as adapters
from evaluation.adapters import BaselineAgentAdapter
from repo_agent.model_router import ModelRouter


def test_baseline_adapter_forwards_uniform_run_call(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_run_graph_agent(**kwargs) -> str:
        calls.append(kwargs)
        return "baseline answer"

    monkeypatch.setattr(adapters, "run_graph_agent", fake_run_graph_agent)
    router = ModelRouter(client=SimpleNamespace())
    adapter = BaselineAgentAdapter(
        router=router,
        capability="simple",
        max_graph_steps=12,
    )
    on_tool_call = lambda name, arguments: None

    answer = adapter.run(
        repo_path=Path("repository"),
        question="Where is the entry point?",
        on_tool_call=on_tool_call,
    )

    assert answer == "baseline answer"
    assert calls == [
        {
            "repo_path": Path("repository"),
            "question": "Where is the entry point?",
            "router": router,
            "capability": "simple",
            "max_graph_steps": 12,
            "on_tool_call": on_tool_call,
        }
    ]
    assert adapter.model_metadata.model == "deepseek-v4-flash"
