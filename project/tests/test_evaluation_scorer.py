import json
from pathlib import Path

import pytest

from evaluation.scorer import (
    EvaluationScoreError,
    generate_report,
    load_evaluation_results,
    render_markdown_report,
    score_evaluation,
    summarize_scores,
)


def make_case(
    case_id: str,
    expected_files: list[str] | None = None,
    expected_symbols: list[str] | None = None,
    category: str = "call_chain",
) -> dict:
    return {
        "case_id": case_id,
        "repository": "sample",
        "question": f"question for {case_id}",
        "expected_files": expected_files or ["src/sample.py"],
        "expected_symbols": expected_symbols or [],
        "category": category,
    }


def make_result(
    case_id: str,
    answer: str | None,
    status: str = "completed",
    tool_calls: list[dict] | None = None,
    elapsed_seconds: float = 2.0,
    error_type: str | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "stage": "baseline",
        "repository": "sample",
        "capability": "simple",
        "model": "deepseek-v4-flash",
        "thinking": "enabled",
        "reasoning_effort": "high",
        "answer": answer,
        "tool_calls": tool_calls or [],
        "elapsed_seconds": elapsed_seconds,
        "status": status,
        "error_type": error_type,
        "error_message": None if status == "completed" else "failed",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_scorer_joins_by_case_id_and_measures_expected_evidence() -> None:
    cases = [
        make_case(
            "case-001",
            expected_files=["src/sample.py", "src/helper.py"],
            expected_symbols=["run_sample"],
        )
    ]
    results = [
        make_result(
            "case-001",
            "`src\\sample.py` defines `run_sample`; another file is omitted.",
            tool_calls=[{"name": "read_file", "arguments": {}}],
        )
    ]

    score = score_evaluation(cases, results)[0]

    assert score["matched_files"] == ["src/sample.py"]
    assert score["missing_files"] == ["src/helper.py"]
    assert score["file_coverage"] == 0.5
    assert score["matched_symbols"] == ["run_sample"]
    assert score["symbol_coverage"] == 1.0
    assert score["evidence_coverage"] == pytest.approx(2 / 3)
    assert score["full_evidence"] is False
    assert score["tool_call_count"] == 1
    assert score["human_correctness"] is None


def test_scorer_counts_failed_result_as_zero_evidence() -> None:
    score = score_evaluation(
        [make_case("case-001", expected_symbols=["run_sample"])],
        [
            make_result(
                "case-001",
                answer=None,
                status="failed",
                error_type="AgentLimitError",
            )
        ],
    )[0]

    assert score["completed"] is False
    assert score["evidence_coverage"] == 0.0
    assert score["error_type"] == "AgentLimitError"


def test_scorer_rejects_missing_or_unknown_case_ids() -> None:
    cases = [make_case("case-001")]

    with pytest.raises(EvaluationScoreError, match="missing evaluation results"):
        score_evaluation(cases, [])

    with pytest.raises(EvaluationScoreError, match="unknown evaluation result"):
        score_evaluation(
            cases,
            [make_result("case-001", "src/sample.py"), make_result("extra", "x")],
        )


def test_result_loader_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    result_path = tmp_path / "results.jsonl"
    row = make_result("case-001", "src/sample.py")
    write_jsonl(result_path, [row, row])

    with pytest.raises(EvaluationScoreError, match="duplicate case_id"):
        load_evaluation_results(result_path)


def test_summary_separates_reliability_from_completed_answer_evidence() -> None:
    cases = [make_case("success"), make_case("failed")]
    results = [
        make_result(
            "success",
            "src/sample.py",
            tool_calls=[{"name": "read_file", "arguments": {}}],
            elapsed_seconds=1.0,
        ),
        make_result(
            "failed",
            None,
            status="failed",
            elapsed_seconds=3.0,
            error_type="AgentLimitError",
        ),
    ]

    summary = summarize_scores("Flash High", score_evaluation(cases, results))

    assert summary["completed_cases"] == 1
    assert summary["completion_rate"] == 0.5
    assert summary["evidence_coverage"] == 0.5
    assert summary["completed_evidence_coverage"] == 1.0
    assert summary["total_tool_calls"] == 1
    assert summary["average_elapsed_seconds"] == 2.0
    assert summary["p95_elapsed_seconds"] == 3.0
    assert summary["failure_types"] == {"AgentLimitError": 1}


def test_report_generation_reads_jsonl_and_writes_markdown(tmp_path: Path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "reports" / "summary.md"
    write_jsonl(cases_path, [make_case("case-001")])
    write_jsonl(results_path, [make_result("case-001", "src/sample.py")])

    summaries = generate_report(
        cases_path=cases_path,
        result_paths={"Flash High": results_path},
        output_path=report_path,
    )

    report = report_path.read_text(encoding="utf-8")
    assert len(summaries) == 1
    assert "# Repo Agent Evaluation Summary" in report
    assert "Flash High" in report
    assert "1/1 (100.0%)" in report
    assert "No model request" not in report


def test_report_renderer_rejects_empty_input() -> None:
    with pytest.raises(EvaluationScoreError, match="empty summary"):
        render_markdown_report([])


def test_generate_report_can_score_one_repository_from_full_results(
    tmp_path: Path,
) -> None:
    cases_path = tmp_path / "cases.jsonl"
    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "summary.md"
    sample_case = make_case("sample-case")
    other_case = {**make_case("other-case"), "repository": "other"}
    sample_result = make_result("sample-case", "src/sample.py")
    other_result = {
        **make_result("other-case", "src/sample.py"),
        "repository": "other",
    }
    write_jsonl(cases_path, [sample_case, other_case])
    write_jsonl(results_path, [sample_result, other_result])

    summaries = generate_report(
        cases_path=cases_path,
        result_paths={"Filtered": results_path},
        output_path=report_path,
        repository="sample",
    )

    assert summaries[0]["total_cases"] == 1
