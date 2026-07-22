import numpy as np
import pytest

from repo_agent.retrieval import CodeChunk
from repo_agent.retrieval.embedder import EmbeddingError
from repo_agent.retrieval.retriever import (
    HybridRetriever,
    RetrievalWarning,
    reciprocal_rank_fusion,
)


def make_chunk(
    chunk_id: str,
    file_path: str,
    symbol_name: str,
    start_line: int,
) -> CodeChunk:
    return CodeChunk(
        chunk_id=chunk_id,
        file_path=file_path,
        symbol_name=symbol_name,
        kind="function",
        start_line=start_line,
        end_line=start_line + 1,
        code=f"def {symbol_name}():\n    return None",
        docstring=None,
        parent_symbol=None,
        content_hash=f"hash-{chunk_id}",
    )


def test_rrf_rewards_chunk_found_by_both_retrieval_methods() -> None:
    shared = make_chunk("shared", "shared.py", "shared", 1)
    keyword_only = make_chunk("keyword", "keyword.py", "keyword_only", 1)
    vector_only = make_chunk("vector", "vector.py", "vector_only", 1)

    results = reciprocal_rank_fusion(
        keyword_chunks=[keyword_only, shared],
        vector_chunks=[vector_only, shared],
        k=60,
    )

    assert results[0].chunk is shared
    assert results[0].sources == ("keyword", "vector")
    assert results[0].keyword_rank == 2
    assert results[0].vector_rank == 2


def test_hybrid_retriever_applies_symbol_and_per_file_limits() -> None:
    duplicate_symbol_low = make_chunk("a-low", "a.py", "same", 10)
    keyword_results = [
        make_chunk("a-1", "a.py", "same", 1),
        duplicate_symbol_low,
        make_chunk("a-2", "a.py", "second", 20),
        make_chunk("a-3", "a.py", "third", 30),
        make_chunk("b-1", "b.py", "other", 1),
    ]

    class FakeIndex:
        def search_keyword(self, query: str, limit: int):
            return keyword_results

        def search_vector(self, query_vector: np.ndarray, limit: int):
            return []

    class FakeEmbedder:
        def embed_query(self, text: str) -> np.ndarray:
            return np.array([1.0], dtype=np.float32)

    retriever = HybridRetriever(
        index=FakeIndex(),  # type: ignore[arg-type]
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        result_limit=10,
        per_file_limit=2,
    )

    results = retriever.retrieve("question")

    assert [(result.chunk.file_path, result.chunk.symbol_name) for result in results] == [
        ("a.py", "same"),
        ("a.py", "second"),
        ("b.py", "other"),
    ]


def test_hybrid_retriever_degrades_to_keyword_results() -> None:
    keyword_chunk = make_chunk("keyword", "keyword.py", "keyword", 1)

    class FakeIndex:
        def search_keyword(self, query: str, limit: int):
            return [keyword_chunk]

        def search_vector(self, query_vector: np.ndarray, limit: int):
            raise AssertionError("vector search should not run")

    class FailingEmbedder:
        def embed_query(self, text: str) -> np.ndarray:
            raise EmbeddingError("local model unavailable")

    retriever = HybridRetriever(
        index=FakeIndex(),  # type: ignore[arg-type]
        embedder=FailingEmbedder(),  # type: ignore[arg-type]
    )

    with pytest.warns(RetrievalWarning, match="semantic retrieval unavailable"):
        results = retriever.retrieve("question")

    assert [result.chunk for result in results] == [keyword_chunk]
    assert results[0].sources == ("keyword",)


def test_hybrid_retriever_rejects_empty_question() -> None:
    retriever = HybridRetriever(
        index=object(),  # type: ignore[arg-type]
        embedder=object(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="question must not be empty"):
        retriever.retrieve(" ")
