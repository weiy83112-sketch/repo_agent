from pathlib import Path
from types import SimpleNamespace

import numpy as np

from repo_agent.langgraph_agent import run_graph_agent
from repo_agent.retrieval import (
    ContextBuilder,
    HybridRetriever,
    PythonAstChunker,
    RepositoryIndex,
    RepositoryScanner,
)


class StaticEmbedder:
    model_name = "static-test-embedder"
    dimension = 2

    def embed_query(self, text: str) -> np.ndarray:
        return np.array([1.0, 0.0], dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32),
            (len(texts), 1),
        )


class FinalMessage:
    content = "The model client is created in model_router.py."
    tool_calls = None

    def model_dump(self, exclude_none=True) -> dict:
        return {"role": "assistant", "content": self.content}


class CapturingRouter:
    def __init__(self) -> None:
        self.messages: list[dict] | None = None

    def complex(self, *, messages, tools):
        self.messages = messages
        return SimpleNamespace(
            choices=[SimpleNamespace(message=FinalMessage())]
        )

    simple = complex


def test_question_flows_from_repository_index_to_model_context(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repository"
    repo_path.mkdir()
    (repo_path / "model_router.py").write_text(
        "def create_model_client():\n"
        "    return OpenAI(base_url='https://api.example.com')\n",
        encoding="utf-8",
    )
    embedder = StaticEmbedder()
    router = CapturingRouter()

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        index.update(
            repo_path=repo_path,
            scanner=RepositoryScanner(),
            chunker=PythonAstChunker(),
            embedder=embedder,
        )
        answer = run_graph_agent(
            repo_path=repo_path,
            question="create_model_client",
            router=router,
            retriever=HybridRetriever(index=index, embedder=embedder),
            context_builder=ContextBuilder(),
        )

    assert answer == "The model client is created in model_router.py."
    assert router.messages is not None
    context = router.messages[0]["content"]
    assert "[file: model_router.py]" in context
    assert "[symbol: create_model_client]" in context
    assert "def create_model_client():" in context
