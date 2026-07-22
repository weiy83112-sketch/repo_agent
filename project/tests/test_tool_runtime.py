from pathlib import Path

import pytest

from repo_agent.tools.registry import execute_tool
from repo_agent.tools.runtime import ToolRuntime


class FakeRetriever:
    def retrieve(self, question: str) -> list[str]:
        return [f"chunk for {question}"]


class FakeContextBuilder:
    def build(self, chunks: list[str]) -> str:
        return f"context: {chunks[0]}"


def test_search_code_uses_retrieval_runtime(tmp_path: Path) -> None:
    runtime = ToolRuntime(
        repo_path=tmp_path,
        retriever=FakeRetriever(),
        context_builder=FakeContextBuilder(),
    )

    result = execute_tool(
        repo_path=tmp_path,
        name="search_code",
        arguments={"query": "model client"},
        runtime=runtime,
    )

    assert result == "context: chunk for model client"


def test_search_code_requires_retrieval_runtime(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unavailable"):
        execute_tool(
            repo_path=tmp_path,
            name="search_code",
            arguments={"query": "model client"},
        )
