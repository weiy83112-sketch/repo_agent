import warnings

from .embedder import Embedder, EmbeddingError
from .index import RepositoryIndex
from .models import CodeChunk, RetrievedChunk


class RetrievalWarning(UserWarning):
    """Semantic retrieval failed and keyword-only retrieval was used."""


class HybridRetriever:
    def __init__(
        self,
        index: RepositoryIndex,
        embedder: Embedder,
        keyword_limit: int = 20,
        vector_limit: int = 20,
        result_limit: int = 10,
        per_file_limit: int = 3,
        rrf_k: int = 60,
    ) -> None:
        for name, value in (
            ("keyword_limit", keyword_limit),
            ("vector_limit", vector_limit),
            ("result_limit", result_limit),
            ("per_file_limit", per_file_limit),
            ("rrf_k", rrf_k),
        ):
            if value < 1:
                raise ValueError(f"{name} must be positive")

        self._index = index
        self._embedder = embedder
        self._keyword_limit = keyword_limit
        self._vector_limit = vector_limit
        self._result_limit = result_limit
        self._per_file_limit = per_file_limit
        self._rrf_k = rrf_k

    def retrieve(
        self,
        question: str,
        limit: int | None = None,
    ) -> list[RetrievedChunk]:
        if not question.strip():
            raise ValueError("question must not be empty")
        result_limit = self._result_limit if limit is None else limit
        if result_limit < 1:
            raise ValueError("limit must be positive")

        keyword_chunks = self._index.search_keyword(
            question,
            limit=self._keyword_limit,
        )
        try:
            question_vector = self._embedder.embed_query(question)
            vector_chunks = self._index.search_vector(
                question_vector,
                limit=self._vector_limit,
            )
        except (EmbeddingError, ValueError) as error:
            warnings.warn(
                f"semantic retrieval unavailable: {error}",
                RetrievalWarning,
                stacklevel=2,
            )
            vector_chunks = []

        fused = reciprocal_rank_fusion(
            keyword_chunks=keyword_chunks,
            vector_chunks=vector_chunks,
            k=self._rrf_k,
        )
        return _select_results(
            fused,
            result_limit=result_limit,
            per_file_limit=self._per_file_limit,
        )


def reciprocal_rank_fusion(
    keyword_chunks: list[CodeChunk],
    vector_chunks: list[CodeChunk],
    k: int = 60,
) -> list[RetrievedChunk]:
    if k < 1:
        raise ValueError("k must be positive")

    candidates: dict[str, dict] = {}
    for source, chunks in (
        ("keyword", keyword_chunks),
        ("vector", vector_chunks),
    ):
        seen_in_source: set[str] = set()
        for rank, chunk in enumerate(chunks, start=1):
            if chunk.chunk_id in seen_in_source:
                continue
            seen_in_source.add(chunk.chunk_id)

            candidate = candidates.setdefault(
                chunk.chunk_id,
                {
                    "chunk": chunk,
                    "score": 0.0,
                    "sources": [],
                    "keyword_rank": None,
                    "vector_rank": None,
                },
            )
            candidate["score"] += 1.0 / (k + rank)
            candidate["sources"].append(source)
            candidate[f"{source}_rank"] = rank

    results = [
        RetrievedChunk(
            chunk=candidate["chunk"],
            score=candidate["score"],
            sources=tuple(candidate["sources"]),
            keyword_rank=candidate["keyword_rank"],
            vector_rank=candidate["vector_rank"],
        )
        for candidate in candidates.values()
    ]
    results.sort(key=_retrieval_sort_key)
    return results


def _select_results(
    results: list[RetrievedChunk],
    result_limit: int,
    per_file_limit: int,
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    file_counts: dict[str, int] = {}
    seen_symbols: set[tuple[str, str, str]] = set()

    for result in results:
        chunk = result.chunk
        symbol_key = (chunk.file_path, chunk.symbol_name, chunk.kind)
        if symbol_key in seen_symbols:
            continue
        if file_counts.get(chunk.file_path, 0) >= per_file_limit:
            continue

        selected.append(result)
        seen_symbols.add(symbol_key)
        file_counts[chunk.file_path] = file_counts.get(chunk.file_path, 0) + 1
        if len(selected) == result_limit:
            break

    return selected


def _retrieval_sort_key(result: RetrievedChunk) -> tuple:
    best_rank = min(
        rank
        for rank in (result.keyword_rank, result.vector_rank)
        if rank is not None
    )
    return (
        -result.score,
        best_rank,
        result.chunk.file_path,
        result.chunk.start_line,
        result.chunk.chunk_id,
    )
