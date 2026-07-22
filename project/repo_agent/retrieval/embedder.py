from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .models import CodeChunk


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_CACHE = PROJECT_DIR / ".cache" / "huggingface"


class EmbeddingError(RuntimeError):
    """Local text embeddings could not be created or validated."""


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_query(self, text: str) -> np.ndarray: ...

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_folder: Path = DEFAULT_MODEL_CACHE,
        local_files_only: bool = True,
        backend: Any | None = None,
    ) -> None:
        if not model_name:
            raise ValueError("model_name must not be empty")

        if backend is None:
            try:
                from sentence_transformers import SentenceTransformer

                backend = SentenceTransformer(
                    model_name,
                    cache_folder=str(cache_folder),
                    local_files_only=local_files_only,
                )
            except Exception as error:
                raise EmbeddingError(
                    f"could not load local embedding model: {model_name}"
                ) from error

        get_dimension = getattr(backend, "get_embedding_dimension", None)
        if get_dimension is None:
            get_dimension = backend.get_sentence_embedding_dimension
        dimension = get_dimension()
        if not isinstance(dimension, int) or dimension < 1:
            raise EmbeddingError("embedding model returned an invalid dimension")

        self._model_name = model_name
        self._dimension = dimension
        self._backend = backend

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> np.ndarray:
        if not text.strip():
            raise ValueError("query text must not be empty")
        return self._encode([f"query: {text}"])[0]

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        if any(not text.strip() for text in texts):
            raise ValueError("passage text must not be empty")
        return self._encode([f"passage: {text}" for text in texts])

    def _encode(self, texts: list[str]) -> np.ndarray:
        try:
            vectors = self._backend.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as error:
            raise EmbeddingError("local embedding generation failed") from error

        array = np.asarray(vectors, dtype=np.float32)
        if array.shape != (len(texts), self.dimension):
            raise EmbeddingError(
                "embedding model returned an unexpected vector shape"
            )
        if not np.isfinite(array).all():
            raise EmbeddingError("embedding model returned non-finite values")

        norms = np.linalg.norm(array, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise EmbeddingError("embedding model returned a zero vector")
        return np.ascontiguousarray(array / norms, dtype=np.float32)


def code_chunk_embedding_text(chunk: CodeChunk) -> str:
    parts = [
        f"path: {chunk.file_path}",
        f"symbol: {chunk.symbol_name}",
        f"kind: {chunk.kind}",
    ]
    if chunk.docstring:
        parts.append(f"docstring: {chunk.docstring}")
    parts.append(chunk.code)
    return "\n".join(parts)
