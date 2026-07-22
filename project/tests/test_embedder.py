import numpy as np
import pytest

from repo_agent.retrieval import CodeChunk
from repo_agent.retrieval.embedder import (
    EmbeddingError,
    SentenceTransformerEmbedder,
    code_chunk_embedding_text,
)


class FakeBackend:
    def __init__(self) -> None:
        self.received_texts: list[list[str]] = []

    def get_embedding_dimension(self) -> int:
        return 3

    def encode(self, texts: list[str], **kwargs) -> np.ndarray:
        self.received_texts.append(texts)
        return np.array(
            [[index + 1.0, 2.0, 3.0] for index, _ in enumerate(texts)],
            dtype=np.float32,
        )


def test_embedder_uses_e5_query_and_passage_prefixes() -> None:
    backend = FakeBackend()
    embedder = SentenceTransformerEmbedder(
        model_name="fake-model",
        backend=backend,
    )

    query_vector = embedder.embed_query("创建模型客户端")
    passage_vectors = embedder.embed_passages(["self._client = OpenAI()"])

    assert backend.received_texts == [
        ["query: 创建模型客户端"],
        ["passage: self._client = OpenAI()"],
    ]
    assert query_vector.shape == (3,)
    assert passage_vectors.shape == (1, 3)
    assert np.linalg.norm(query_vector) == pytest.approx(1.0)
    assert np.linalg.norm(passage_vectors[0]) == pytest.approx(1.0)


def test_embedder_returns_typed_empty_passage_matrix() -> None:
    embedder = SentenceTransformerEmbedder(
        model_name="fake-model",
        backend=FakeBackend(),
    )

    vectors = embedder.embed_passages([])

    assert vectors.shape == (0, 3)
    assert vectors.dtype == np.float32


def test_embedder_rejects_empty_text() -> None:
    embedder = SentenceTransformerEmbedder(
        model_name="fake-model",
        backend=FakeBackend(),
    )

    with pytest.raises(ValueError, match="query text must not be empty"):
        embedder.embed_query("  ")
    with pytest.raises(ValueError, match="passage text must not be empty"):
        embedder.embed_passages([""])


def test_embedder_rejects_invalid_backend_shape() -> None:
    class InvalidBackend(FakeBackend):
        def encode(self, texts: list[str], **kwargs) -> np.ndarray:
            return np.ones((len(texts), 2), dtype=np.float32)

    embedder = SentenceTransformerEmbedder(
        model_name="fake-model",
        backend=InvalidBackend(),
    )

    with pytest.raises(EmbeddingError, match="unexpected vector shape"):
        embedder.embed_query("question")


def test_code_chunk_embedding_text_contains_searchable_evidence() -> None:
    chunk = CodeChunk(
        chunk_id="chunk-1",
        file_path="repo_agent/model_router.py",
        symbol_name="ModelRouter.__init__",
        kind="method",
        start_line=49,
        end_line=64,
        code="def __init__(self):\n    self._client = OpenAI()",
        docstring="Create the model client.",
        parent_symbol="ModelRouter",
        content_hash="hash-1",
    )

    text = code_chunk_embedding_text(chunk)

    assert "path: repo_agent/model_router.py" in text
    assert "symbol: ModelRouter.__init__" in text
    assert "docstring: Create the model client." in text
    assert "self._client = OpenAI()" in text
