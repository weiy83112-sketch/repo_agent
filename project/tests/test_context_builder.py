from repo_agent.retrieval import CodeChunk, RetrievedChunk
from repo_agent.retrieval.context_builder import (
    ContextBuilder,
    NO_BUDGET_CONTEXT,
    NO_RETRIEVAL_CONTEXT,
)


def make_retrieved(
    chunk_id: str,
    file_path: str,
    symbol_name: str,
    code: str,
    score: float,
) -> RetrievedChunk:
    chunk = CodeChunk(
        chunk_id=chunk_id,
        file_path=file_path,
        symbol_name=symbol_name,
        kind="function",
        start_line=10,
        end_line=11,
        code=code,
        docstring=None,
        parent_symbol=None,
        content_hash=f"hash-{chunk_id}",
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        sources=("keyword", "vector"),
        keyword_rank=1,
        vector_rank=2,
    )


def test_context_builder_formats_traceable_evidence() -> None:
    retrieved = make_retrieved(
        "chunk-1",
        "repo_agent/model_router.py",
        "ModelRouter.complex",
        "def complex():\n    return None",
        0.0322,
    )

    context = ContextBuilder().build([retrieved])

    assert "[file: repo_agent/model_router.py]" in context
    assert "[symbol: ModelRouter.complex]" in context
    assert "[lines: 10-11]" in context
    assert "[source: keyword, vector]" in context
    assert "def complex():" in context


def test_context_builder_keeps_whole_blocks_within_budget() -> None:
    class FixedEstimator:
        def estimate(self, text: str) -> int:
            return 6

    first = make_retrieved("first", "a.py", "first", "def first(): pass", 0.03)
    second = make_retrieved("second", "b.py", "second", "def second(): pass", 0.02)

    context = ContextBuilder(
        token_budget=6,
        token_estimator=FixedEstimator(),
    ).build([first, second])

    assert "def first(): pass" in context
    assert "def second(): pass" not in context


def test_context_builder_reports_empty_and_too_small_budget() -> None:
    class LargeEstimator:
        def estimate(self, text: str) -> int:
            return 100

    retrieved = make_retrieved("chunk", "a.py", "run", "def run(): pass", 0.03)

    assert ContextBuilder().build([]) == NO_RETRIEVAL_CONTEXT
    assert ContextBuilder(
        token_budget=1,
        token_estimator=LargeEstimator(),
    ).build([retrieved]) == NO_BUDGET_CONTEXT
