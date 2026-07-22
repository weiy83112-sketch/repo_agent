from evaluation.retrieval_scorer import (
    is_relevant_chunk,
    score_ranked_chunks,
    summarize_retrieval_scores,
)
from repo_agent.retrieval import CodeChunk


def make_chunk(path: str, symbol: str) -> CodeChunk:
    return CodeChunk(
        chunk_id=f"{path}:{symbol}",
        file_path=path,
        symbol_name=symbol,
        kind="function",
        start_line=1,
        end_line=2,
        code=f"def {symbol.rsplit('.', 1)[-1]}():\n    pass",
        docstring=None,
        parent_symbol=None,
        content_hash=f"hash:{path}:{symbol}",
    )


CASE = {
    "case_id": "case-1",
    "repository": "repo",
    "question": "Where is the entry point?",
    "expected_files": ["src/package/main.py"],
    "expected_symbols": ["main"],
    "category": "entry_point",
}


def test_relevance_matches_expected_path_or_qualified_symbol() -> None:
    assert is_relevant_chunk(make_chunk("src/package/main.py", "other"), CASE)
    assert is_relevant_chunk(make_chunk("src/other.py", "Runner.main"), CASE)
    assert not is_relevant_chunk(make_chunk("src/other.py", "maintain"), CASE)


def test_score_uses_first_relevant_rank_within_top_five() -> None:
    chunks = [
        make_chunk("src/other.py", "first"),
        make_chunk("src/package/main.py", "main"),
    ]

    score = score_ranked_chunks(CASE, "hybrid", chunks, 0.1)

    assert score["hit_at_5"] is True
    assert score["first_relevant_rank"] == 2
    assert score["reciprocal_rank"] == 0.5
    assert score["retrieved"][1]["relevant"] is True


def test_summary_calculates_recall_and_mrr() -> None:
    hit = score_ranked_chunks(
        CASE,
        "keyword",
        [make_chunk("src/package/main.py", "main")],
        0.1,
    )
    miss = score_ranked_chunks(
        {**CASE, "case_id": "case-2"},
        "keyword",
        [make_chunk("src/other.py", "other")],
        0.3,
    )

    summary = summarize_retrieval_scores([hit, miss])[0]

    assert summary["hits_at_5"] == 1
    assert summary["recall_at_5"] == 0.5
    assert summary["mrr"] == 0.5
    assert summary["average_elapsed_seconds"] == 0.2
