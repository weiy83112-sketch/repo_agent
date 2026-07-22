import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import TypedDict

from evaluation.loader import load_evaluation_cases, validate_evaluation_evidence
from evaluation.repositories import load_repository_paths
from evaluation.schemas import EvaluationCase
from repo_agent.retrieval import (
    CodeChunk,
    HybridRetriever,
    PythonAstChunker,
    RepositoryIndex,
    RepositoryScanner,
    SentenceTransformerEmbedder,
    default_index_path,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_DIR.parent
EVALUATION_DIR = PROJECT_DIR / "evaluation"
METHODS = ("keyword", "vector", "hybrid")


class RetrievalCaseScore(TypedDict):
    case_id: str
    repository: str
    category: str
    method: str
    hit_at_5: bool
    reciprocal_rank: float
    first_relevant_rank: int | None
    elapsed_seconds: float
    retrieved: list[dict]


class RetrievalSummary(TypedDict):
    method: str
    total_cases: int
    hits_at_5: int
    recall_at_5: float
    mrr: float
    average_elapsed_seconds: float
    p95_elapsed_seconds: float


def is_relevant_chunk(chunk: CodeChunk, case: EvaluationCase) -> bool:
    normalized_path = chunk.file_path.replace("\\", "/").casefold()
    expected_paths = {
        path.replace("\\", "/").casefold()
        for path in case["expected_files"]
    }
    if normalized_path in expected_paths:
        return True

    return any(
        chunk.symbol_name == symbol
        or chunk.symbol_name.endswith(f".{symbol}")
        for symbol in case["expected_symbols"]
    )


def score_ranked_chunks(
    case: EvaluationCase,
    method: str,
    chunks: list[CodeChunk],
    elapsed_seconds: float,
) -> RetrievalCaseScore:
    first_relevant_rank = next(
        (
            rank
            for rank, chunk in enumerate(chunks[:5], start=1)
            if is_relevant_chunk(chunk, case)
        ),
        None,
    )
    return {
        "case_id": case["case_id"],
        "repository": case["repository"],
        "category": case["category"],
        "method": method,
        "hit_at_5": first_relevant_rank is not None,
        "reciprocal_rank": (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        ),
        "first_relevant_rank": first_relevant_rank,
        "elapsed_seconds": elapsed_seconds,
        "retrieved": [
            {
                "rank": rank,
                "file_path": chunk.file_path,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "relevant": is_relevant_chunk(chunk, case),
            }
            for rank, chunk in enumerate(chunks[:5], start=1)
        ],
    }


def summarize_retrieval_scores(
    scores: list[RetrievalCaseScore],
) -> list[RetrievalSummary]:
    grouped: dict[str, list[RetrievalCaseScore]] = defaultdict(list)
    for score in scores:
        grouped[score["method"]].append(score)

    summaries: list[RetrievalSummary] = []
    for method in METHODS:
        method_scores = grouped.get(method, [])
        if not method_scores:
            continue
        elapsed = sorted(score["elapsed_seconds"] for score in method_scores)
        p95_index = max(0, math.ceil(0.95 * len(elapsed)) - 1)
        hits = sum(score["hit_at_5"] for score in method_scores)
        summaries.append(
            {
                "method": method,
                "total_cases": len(method_scores),
                "hits_at_5": hits,
                "recall_at_5": hits / len(method_scores),
                "mrr": mean(score["reciprocal_rank"] for score in method_scores),
                "average_elapsed_seconds": mean(elapsed),
                "p95_elapsed_seconds": elapsed[p95_index],
            }
        )
    return summaries


def run_retrieval_evaluation(
    cases: list[EvaluationCase],
    repo_paths: dict[str, Path],
    embedder: SentenceTransformerEmbedder,
) -> list[RetrievalCaseScore]:
    cases_by_repository: dict[str, list[EvaluationCase]] = defaultdict(list)
    for case in cases:
        cases_by_repository[case["repository"]].append(case)

    scores: list[RetrievalCaseScore] = []
    for repository, repository_cases in cases_by_repository.items():
        repo_path = repo_paths[repository]
        with RepositoryIndex(default_index_path(repo_path)) as index:
            index.update(
                repo_path=repo_path,
                scanner=RepositoryScanner(),
                chunker=PythonAstChunker(),
                embedder=embedder,
            )
            retriever = HybridRetriever(index=index, embedder=embedder)

            for case in repository_cases:
                question = case["question"]

                started_at = perf_counter()
                keyword_chunks = index.search_keyword(question, limit=5)
                keyword_elapsed = perf_counter() - started_at
                scores.append(
                    score_ranked_chunks(
                        case,
                        "keyword",
                        keyword_chunks,
                        keyword_elapsed,
                    )
                )

                started_at = perf_counter()
                query_vector = embedder.embed_query(question)
                vector_chunks = index.search_vector(query_vector, limit=5)
                vector_elapsed = perf_counter() - started_at
                scores.append(
                    score_ranked_chunks(
                        case,
                        "vector",
                        vector_chunks,
                        vector_elapsed,
                    )
                )

                started_at = perf_counter()
                hybrid_results = retriever.retrieve(question, limit=5)
                hybrid_elapsed = perf_counter() - started_at
                scores.append(
                    score_ranked_chunks(
                        case,
                        "hybrid",
                        [result.chunk for result in hybrid_results],
                        hybrid_elapsed,
                    )
                )

    return scores


def render_retrieval_report(summaries: list[RetrievalSummary]) -> str:
    lines = [
        "# Hybrid RAG Retrieval Evaluation",
        "",
        "`Recall@5` 表示固定题目的正确文件或符号是否出现在前五个候选中；"
        "`MRR` 衡量第一个正确候选的排名。该报告不调用回答模型。",
        "",
        "| Method | Hits@5 | Recall@5 | MRR | Avg query | P95 query |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        lines.append(
            "| {method} | {hits}/{total} | {recall:.1%} | {mrr:.3f} | "
            "{average:.3f}s | {p95:.3f}s |".format(
                method=summary["method"],
                hits=summary["hits_at_5"],
                total=summary["total_cases"],
                recall=summary["recall_at_5"],
                mrr=summary["mrr"],
                average=summary["average_elapsed_seconds"],
                p95=summary["p95_elapsed_seconds"],
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- A hit requires an exact expected repository-relative file path or an exact/qualified expected symbol.",
            "- Retrieval metrics isolate evidence selection; final answer quality is measured separately with saved DeepSeek results.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score keyword, vector, and hybrid retrieval without a model.",
    )
    parser.add_argument(
        "--repository",
        choices=["repo_agent", "pytest", "django"],
        help="score only cases for one repository",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_evaluation_cases(EVALUATION_DIR / "data" / "cases.jsonl")
    if args.repository is not None:
        cases = [
            case
            for case in cases
            if case["repository"] == args.repository
        ]
    repo_paths = load_repository_paths(
        path=EVALUATION_DIR / "data" / "repositories.json",
        workspace_root=WORKSPACE_ROOT,
        extra_repo_paths={"repo_agent": PROJECT_DIR},
    )
    validate_evaluation_evidence(cases=cases, repo_paths=repo_paths)

    scores = run_retrieval_evaluation(
        cases=cases,
        repo_paths=repo_paths,
        embedder=SentenceTransformerEmbedder(local_files_only=True),
    )
    summaries = summarize_retrieval_scores(scores)

    reports_dir = EVALUATION_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{args.repository}" if args.repository is not None else ""
    details_path = reports_dir / f"retrieval-details{suffix}.jsonl"
    details_path.write_text(
        "".join(json.dumps(score, ensure_ascii=False) + "\n" for score in scores),
        encoding="utf-8",
    )
    summary_path = reports_dir / f"retrieval-summary{suffix}.md"
    summary_path.write_text(render_retrieval_report(summaries), encoding="utf-8")

    print(f"Scored {len(cases)} cases with {len(summaries)} methods.")
    print(f"Report: {summary_path}")
    print("No model request was sent.")


if __name__ == "__main__":
    main()
