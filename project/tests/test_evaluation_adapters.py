from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import evaluation.adapters as adapters
from evaluation.adapters import BaselineAgentAdapter, HybridRagAgentAdapter
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


class StaticEmbedder:
    model_name = "static-adapter-test"
    dimension = 2

    def embed_query(self, text: str) -> np.ndarray:
        return np.array([1.0, 0.0], dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32),
            (len(texts), 1),
        )


def test_hybrid_adapter_builds_once_and_forwards_rag_dependencies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repository"
    repo_path.mkdir()
    (repo_path / "module.py").write_text(
        "def target_symbol():\n    return 1\n",
        encoding="utf-8",
    )
    calls: list[dict] = []

    def fake_run_graph_agent(**kwargs) -> str:
        calls.append(kwargs)
        return "hybrid answer"

    monkeypatch.setattr(adapters, "run_graph_agent", fake_run_graph_agent)
    router = ModelRouter(client=SimpleNamespace())
    adapter = HybridRagAgentAdapter(
        router=router,
        capability="complex",
        max_graph_steps=14,
        embedder=StaticEmbedder(),
        index_path_factory=lambda repo: tmp_path / "indexes" / "index.sqlite3",
    )

    try:
        first_answer = adapter.run(repo_path, "first question", None)
        second_answer = adapter.run(repo_path, "second question", None)

        assert first_answer == second_answer == "hybrid answer"
        assert len(calls) == 2
        assert calls[0]["retriever"] is calls[1]["retriever"]
        assert calls[0]["context_builder"] is calls[1]["context_builder"]
        assert calls[0]["repo_path"] == repo_path
        assert calls[0]["question"] == "first question"
        assert calls[0]["router"] is router
        assert calls[0]["capability"] == "complex"
        assert calls[0]["max_graph_steps"] == 14
        retrieved = calls[0]["retriever"].retrieve("target_symbol")
        assert retrieved[0].chunk.symbol_name == "target_symbol"
    finally:
        adapter.close()

    with pytest.raises(RuntimeError, match="is closed"):
        adapter.run(repo_path, "after close", None)


def test_hybrid_adapter_context_manager_closes_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repository"
    repo_path.mkdir()
    (repo_path / "module.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(adapters, "run_graph_agent", lambda **kwargs: "answer")

    adapter = HybridRagAgentAdapter(
        router=ModelRouter(client=SimpleNamespace()),
        capability="simple",
        embedder=StaticEmbedder(),
        index_path_factory=lambda repo: tmp_path / "index.sqlite3",
    )
    with adapter:
        assert adapter.run(repo_path, "question", None) == "answer"

    with pytest.raises(RuntimeError, match="is closed"):
        adapter.run(repo_path, "question", None)
