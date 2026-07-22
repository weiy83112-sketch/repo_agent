from dataclasses import FrozenInstanceError

import pytest

from repo_agent.retrieval import CodeChunk, RetrievedChunk


def make_code_chunk() -> CodeChunk:
    return CodeChunk(
        chunk_id="repo_agent/model_router.py::ModelRouter.complex",
        file_path="repo_agent/model_router.py",
        symbol_name="ModelRouter.complex",
        kind="method",
        start_line=95,
        end_line=98,
        code='def complex(self, messages, tools):\n    return self._complete("complex", messages, tools)',
        docstring="Use the complex model capability.",
        parent_symbol="ModelRouter",
        content_hash="6c9b30d6",
    )


def test_code_chunk_preserves_traceable_source_metadata() -> None:
    chunk = make_code_chunk()

    assert chunk.file_path == "repo_agent/model_router.py"
    assert chunk.symbol_name == "ModelRouter.complex"
    assert chunk.kind == "method"
    assert (chunk.start_line, chunk.end_line) == (95, 98)


def test_code_chunk_is_immutable() -> None:
    chunk = make_code_chunk()

    with pytest.raises(FrozenInstanceError):
        chunk.start_line = 96  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("chunk_id", "", "chunk_id must not be empty"),
        ("file_path", "", "file_path must not be empty"),
        ("symbol_name", "", "symbol_name must not be empty"),
        ("kind", "unsupported", "unsupported chunk kind"),
        ("start_line", 0, "start_line must be at least 1"),
        ("end_line", 94, "end_line must not be before start_line"),
        ("code", "", "code must not be empty"),
        ("content_hash", "", "content_hash must not be empty"),
    ],
)
def test_code_chunk_rejects_invalid_source_metadata(
    field: str,
    value: object,
    message: str,
) -> None:
    values = {
        "chunk_id": "chunk-1",
        "file_path": "package/module.py",
        "symbol_name": "function_name",
        "kind": "function",
        "start_line": 95,
        "end_line": 98,
        "code": "def function_name():\n    return 1",
        "docstring": None,
        "parent_symbol": None,
        "content_hash": "hash-1",
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        CodeChunk(**values)  # type: ignore[arg-type]


def test_retrieved_chunk_records_hybrid_ranking_without_changing_chunk() -> None:
    chunk = make_code_chunk()

    retrieved = RetrievedChunk(
        chunk=chunk,
        score=0.0322,
        sources=("keyword", "vector"),
        keyword_rank=3,
        vector_rank=1,
    )

    assert retrieved.chunk is chunk
    assert retrieved.sources == ("keyword", "vector")
    assert retrieved.keyword_rank == 3
    assert retrieved.vector_rank == 1


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {"score": -0.1, "sources": ("keyword",), "keyword_rank": 1},
            "score must be a finite non-negative number",
        ),
        (
            {"score": float("nan"), "sources": ("keyword",), "keyword_rank": 1},
            "score must be a finite non-negative number",
        ),
        ({"score": 0.1, "sources": ()}, "sources must not be empty"),
        (
            {
                "score": 0.1,
                "sources": ("keyword", "keyword"),
                "keyword_rank": 1,
            },
            "sources must not contain duplicates",
        ),
        (
            {"score": 0.1, "sources": ("other",)},
            "unsupported retrieval sources: other",
        ),
        (
            {"score": 0.1, "sources": ("keyword",), "keyword_rank": None},
            "keyword_rank must be a positive integer",
        ),
        (
            {"score": 0.1, "sources": ("vector",), "keyword_rank": 1, "vector_rank": 2},
            "keyword_rank requires the keyword source",
        ),
        (
            {"score": 0.1, "sources": ("vector",), "vector_rank": 0},
            "vector_rank must be a positive integer",
        ),
    ],
)
def test_retrieved_chunk_rejects_inconsistent_ranking_metadata(
    values: dict,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        RetrievedChunk(chunk=make_code_chunk(), **values)
