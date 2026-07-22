from pathlib import Path

import numpy as np
import pytest

from repo_agent.retrieval.chunker import PythonAstChunker
from repo_agent.retrieval.embedder import EmbeddingError
from repo_agent.retrieval.index import (
    EmbeddingProfileError,
    RepositoryIndex,
    RepositoryIndexWarning,
)
from repo_agent.retrieval.scanner import RepositoryScanner


class FakeEmbedder:
    model_name = "fake-embedding-model"
    dimension = 2

    def __init__(self) -> None:
        self.passage_calls: list[list[str]] = []

    def embed_query(self, text: str) -> np.ndarray:
        if "beta" in text:
            return np.array([0.0, 1.0], dtype=np.float32)
        return np.array([1.0, 0.0], dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        self.passage_calls.append(texts)
        return np.array(
            [
                [0.0, 1.0] if "beta_value" in text else [1.0, 0.0]
                for text in texts
            ],
            dtype=np.float32,
        )


def update_index(
    index: RepositoryIndex,
    repo_path: Path,
    embedder: FakeEmbedder | None,
):
    return index.update(
        repo_path=repo_path,
        scanner=RepositoryScanner(),
        chunker=PythonAstChunker(),
        embedder=embedder,
    )


def make_semantic_repository(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "values.py").write_text(
        "def alpha_value():\n"
        "    return 'alpha'\n"
        "\n"
        "def beta_value():\n"
        "    return 'beta'\n",
        encoding="utf-8",
    )
    return repo_path


def test_update_persists_embedding_profile_and_vector_ranking(tmp_path: Path) -> None:
    repo_path = make_semantic_repository(tmp_path)
    embedder = FakeEmbedder()

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        summary = update_index(index, repo_path, embedder)
        results = index.search_vector(embedder.embed_query("find beta"))

        assert index.embedding_profile() == ("fake-embedding-model", 2)
        assert summary.embedded_chunks == 2
        assert results[0].symbol_name == "beta_value"


def test_unchanged_embedded_files_are_not_embedded_again(tmp_path: Path) -> None:
    repo_path = make_semantic_repository(tmp_path)
    embedder = FakeEmbedder()

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path, embedder)
        second = update_index(index, repo_path, embedder)

    assert len(embedder.passage_calls) == 1
    assert second.unchanged_files == 1
    assert second.embedded_chunks == 0


def test_existing_keyword_index_backfills_missing_embeddings(tmp_path: Path) -> None:
    repo_path = make_semantic_repository(tmp_path)
    embedder = FakeEmbedder()

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path, None)
        backfill = update_index(index, repo_path, embedder)
        results = index.search_vector(embedder.embed_query("find beta"))

    assert backfill.indexed_chunks == 0
    assert backfill.embedded_chunks == 2
    assert results[0].symbol_name == "beta_value"


def test_embedding_failure_keeps_keyword_index_available(tmp_path: Path) -> None:
    repo_path = make_semantic_repository(tmp_path)

    class FailingEmbedder(FakeEmbedder):
        def embed_passages(self, texts: list[str]) -> np.ndarray:
            raise EmbeddingError("expected test failure")

    embedder = FailingEmbedder()
    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        with pytest.warns(RepositoryIndexWarning, match="without embeddings"):
            summary = update_index(index, repo_path, embedder)

        assert summary.embedded_chunks == 0
        assert index.search_vector(embedder.embed_query("find beta")) == []
        assert index.search_keyword("beta_value")[0].symbol_name == "beta_value"


def test_embedding_profile_change_requires_rebuild(tmp_path: Path) -> None:
    repo_path = make_semantic_repository(tmp_path)

    class DifferentEmbedder(FakeEmbedder):
        model_name = "different-model"

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path, FakeEmbedder())

        with pytest.raises(EmbeddingProfileError, match="rebuild"):
            update_index(index, repo_path, DifferentEmbedder())


def test_vector_search_validates_query_dimension_and_zero_vector(
    tmp_path: Path,
) -> None:
    repo_path = make_semantic_repository(tmp_path)

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path, FakeEmbedder())

        with pytest.raises(ValueError, match=r"shape \(2,\)"):
            index.search_vector(np.array([1.0, 2.0, 3.0], dtype=np.float32))
        with pytest.raises(ValueError, match="must not be zero"):
            index.search_vector(np.zeros(2, dtype=np.float32))
