import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import TypedDict, cast

from evaluation.loader import load_evaluation_cases
from evaluation.schemas import EvaluationCase, EvaluationScore


EVALUATION_DIR = Path(__file__).resolve().parent


class EvaluationScoreError(ValueError):
    """评测结果不能与固定题库安全对齐或统计。"""


class CategorySummary(TypedDict):
    total_cases: int
    completed_cases: int
    completion_rate: float
    evidence_coverage: float


class EvaluationSummary(TypedDict):
    label: str
    stage: str
    capability: str
    model: str
    total_cases: int
    completed_cases: int
    failed_cases: int
    completion_rate: float
    evidence_coverage: float
    completed_evidence_coverage: float
    full_evidence_cases: int
    full_evidence_rate: float
    total_tool_calls: int
    average_tool_calls: float
    total_elapsed_seconds: float
    average_elapsed_seconds: float
    p95_elapsed_seconds: float
    failure_types: dict[str, int]
    by_category: dict[str, CategorySummary]


REQUIRED_RESULT_FIELDS = {
    "case_id",
    "stage",
    "repository",
    "capability",
    "model",
    "answer",
    "tool_calls",
    "elapsed_seconds",
    "status",
    "error_type",
}


def load_evaluation_results(path: Path) -> list[dict]:
    """读取 Runner 生成的 JSONL，并拒绝损坏或重复的结果。"""

    results: list[dict] = []
    seen_case_ids: set[str] = set()

    with path.open("r", encoding="utf-8") as result_file:
        for line_number, raw_line in enumerate(result_file, start=1):
            location = f"{path}:{line_number}"
            try:
                result = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise EvaluationScoreError(f"{location}: invalid result JSON") from error

            if not isinstance(result, dict):
                raise EvaluationScoreError(f"{location}: result must be an object")

            missing = REQUIRED_RESULT_FIELDS - result.keys()
            if missing:
                names = ", ".join(sorted(missing))
                raise EvaluationScoreError(
                    f"{location}: missing result fields: {names}"
                )

            case_id = result["case_id"]
            if not isinstance(case_id, str) or not case_id.strip():
                raise EvaluationScoreError(
                    f"{location}: case_id must be a non-empty string"
                )
            if case_id in seen_case_ids:
                raise EvaluationScoreError(f"{location}: duplicate case_id: {case_id}")

            status = result["status"]
            if status not in {"completed", "failed"}:
                raise EvaluationScoreError(f"{location}: invalid result status")
            if status == "completed" and (
                not isinstance(result["answer"], str)
                or not result["answer"].strip()
            ):
                raise EvaluationScoreError(
                    f"{location}: completed result must contain an answer"
                )
            if status == "failed" and result["answer"] is not None:
                raise EvaluationScoreError(
                    f"{location}: failed result answer must be null"
                )
            if not isinstance(result["tool_calls"], list):
                raise EvaluationScoreError(f"{location}: tool_calls must be a list")
            if (
                not isinstance(result["elapsed_seconds"], (int, float))
                or isinstance(result["elapsed_seconds"], bool)
                or result["elapsed_seconds"] < 0
            ):
                raise EvaluationScoreError(
                    f"{location}: elapsed_seconds must be non-negative"
                )

            seen_case_ids.add(case_id)
            results.append(result)

    return results


def _match_expected_files(answer: str, expected_files: list[str]) -> list[str]:
    # 统一路径分隔符和大小写，使 Markdown 中的 Windows/Unix 路径都能匹配。
    normalized_answer = answer.replace("\\", "/").casefold()
    return [
        path
        for path in expected_files
        if path.replace("\\", "/").casefold() in normalized_answer
    ]


def _match_expected_symbols(answer: str, expected_symbols: list[str]) -> list[str]:
    # Python 标识符区分大小写，因此符号保持精确大小写匹配。
    return [symbol for symbol in expected_symbols if symbol in answer]


def score_evaluation(
    cases: list[EvaluationCase],
    results: list[dict],
) -> list[EvaluationScore]:
    """使用 case_id 连接固定题目和结果，生成每题的确定性自动评分。"""

    cases_by_id = {case["case_id"]: case for case in cases}
    if len(cases_by_id) != len(cases):
        raise EvaluationScoreError("evaluation cases contain duplicate case_id values")

    results_by_id = {result["case_id"]: result for result in results}
    if len(results_by_id) != len(results):
        raise EvaluationScoreError("evaluation results contain duplicate case_id values")

    missing_results = cases_by_id.keys() - results_by_id.keys()
    extra_results = results_by_id.keys() - cases_by_id.keys()
    if missing_results:
        names = ", ".join(sorted(missing_results))
        raise EvaluationScoreError(f"missing evaluation results: {names}")
    if extra_results:
        names = ", ".join(sorted(extra_results))
        raise EvaluationScoreError(f"unknown evaluation result case_id: {names}")

    scores: list[EvaluationScore] = []
    for case in cases:
        result = results_by_id[case["case_id"]]
        if result["repository"] != case["repository"]:
            raise EvaluationScoreError(
                f"{case['case_id']}: result repository does not match case"
            )

        completed = result["status"] == "completed"
        answer = result["answer"] if completed else ""
        matched_files = _match_expected_files(answer, case["expected_files"])
        matched_symbols = _match_expected_symbols(answer, case["expected_symbols"])
        missing_files = [
            path for path in case["expected_files"] if path not in matched_files
        ]
        missing_symbols = [
            symbol
            for symbol in case["expected_symbols"]
            if symbol not in matched_symbols
        ]

        expected_file_count = len(case["expected_files"])
        expected_symbol_count = len(case["expected_symbols"])
        expected_evidence_count = expected_file_count + expected_symbol_count
        matched_evidence_count = len(matched_files) + len(matched_symbols)

        score: EvaluationScore = {
            "case_id": case["case_id"],
            "repository": case["repository"],
            "category": case["category"],
            "stage": result["stage"],
            "capability": result["capability"],
            "model": result["model"],
            "completed": completed,
            "matched_files": matched_files,
            "missing_files": missing_files,
            "file_coverage": len(matched_files) / expected_file_count,
            "matched_symbols": matched_symbols,
            "missing_symbols": missing_symbols,
            "symbol_coverage": (
                len(matched_symbols) / expected_symbol_count
                if expected_symbol_count
                else None
            ),
            "evidence_coverage": matched_evidence_count / expected_evidence_count,
            "full_evidence": matched_evidence_count == expected_evidence_count,
            "tool_call_count": len(result["tool_calls"]),
            "elapsed_seconds": float(result["elapsed_seconds"]),
            "error_type": result["error_type"],
            # 正确性必须人工阅读答案后填写，不能由字符串命中自动替代。
            "human_correctness": None,
        }
        scores.append(score)

    return scores


def _evidence_totals(scores: list[EvaluationScore]) -> tuple[int, int]:
    matched = 0
    expected = 0
    for score in scores:
        matched += len(score["matched_files"]) + len(score["matched_symbols"])
        expected += (
            len(score["matched_files"])
            + len(score["missing_files"])
            + len(score["matched_symbols"])
            + len(score["missing_symbols"])
        )
    return matched, expected


def _nearest_rank_percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def summarize_scores(label: str, scores: list[EvaluationScore]) -> EvaluationSummary:
    """把每题评分汇总成可以跨 Agent、跨模型比较的一组指标。"""

    if not scores:
        raise EvaluationScoreError("cannot summarize an empty score list")

    metadata_fields = ("stage", "capability", "model")
    for field in metadata_fields:
        values = {score[field] for score in scores}
        if len(values) != 1:
            raise EvaluationScoreError(f"scores contain mixed {field} values")

    completed_scores = [score for score in scores if score["completed"]]
    matched_evidence, expected_evidence = _evidence_totals(scores)
    completed_matched, completed_expected = _evidence_totals(completed_scores)
    elapsed_values = [score["elapsed_seconds"] for score in scores]
    failure_types = Counter(
        score["error_type"] or "UnknownError"
        for score in scores
        if not score["completed"]
    )

    category_scores: dict[str, list[EvaluationScore]] = defaultdict(list)
    for score in scores:
        category_scores[score["category"]].append(score)

    by_category: dict[str, CategorySummary] = {}
    for category, group in sorted(category_scores.items()):
        group_completed = sum(score["completed"] for score in group)
        group_matched, group_expected = _evidence_totals(group)
        by_category[category] = {
            "total_cases": len(group),
            "completed_cases": group_completed,
            "completion_rate": group_completed / len(group),
            "evidence_coverage": group_matched / group_expected,
        }

    first = scores[0]
    full_evidence_cases = sum(score["full_evidence"] for score in scores)
    return {
        "label": label,
        "stage": first["stage"],
        "capability": first["capability"],
        "model": first["model"],
        "total_cases": len(scores),
        "completed_cases": len(completed_scores),
        "failed_cases": len(scores) - len(completed_scores),
        "completion_rate": len(completed_scores) / len(scores),
        "evidence_coverage": matched_evidence / expected_evidence,
        "completed_evidence_coverage": (
            completed_matched / completed_expected if completed_expected else 0.0
        ),
        "full_evidence_cases": full_evidence_cases,
        "full_evidence_rate": full_evidence_cases / len(scores),
        "total_tool_calls": sum(score["tool_call_count"] for score in scores),
        "average_tool_calls": mean(
            score["tool_call_count"] for score in scores
        ),
        "total_elapsed_seconds": sum(elapsed_values),
        "average_elapsed_seconds": mean(elapsed_values),
        "p95_elapsed_seconds": _nearest_rank_percentile(elapsed_values, 0.95),
        "failure_types": dict(sorted(failure_types.items())),
        "by_category": by_category,
    }


def render_markdown_report(summaries: list[EvaluationSummary]) -> str:
    """把一个或多个汇总结果渲染成适合作品集保存的 Markdown 报告。"""

    if not summaries:
        raise EvaluationScoreError("cannot render an empty summary list")

    lines = [
        "# Repo Agent Evaluation Summary",
        "",
        "自动证据覆盖率只表示答案是否提到固定题库中的标准文件和符号，"
        "不等同于回答正确性。人工正确性评分（0/1/2）尚未填写。",
        "",
        "## Overall",
        "",
        "| Run | Model | Completed | Evidence | Completed evidence | Full evidence | Tools | Avg time | P95 time |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for summary in summaries:
        lines.append(
            "| {label} | {model} | {completed}/{total} ({completion:.1%}) | "
            "{evidence:.1%} | {completed_evidence:.1%} | "
            "{full}/{total} ({full_rate:.1%}) | {tools} | {average:.2f}s | "
            "{p95:.2f}s |".format(
                label=summary["label"],
                model=summary["model"],
                completed=summary["completed_cases"],
                total=summary["total_cases"],
                completion=summary["completion_rate"],
                evidence=summary["evidence_coverage"],
                completed_evidence=summary["completed_evidence_coverage"],
                full=summary["full_evidence_cases"],
                full_rate=summary["full_evidence_rate"],
                tools=summary["total_tool_calls"],
                average=summary["average_elapsed_seconds"],
                p95=summary["p95_elapsed_seconds"],
            )
        )

    lines.extend(["", "## Failures", ""])
    for summary in summaries:
        failures = ", ".join(
            f"{name}: {count}"
            for name, count in summary["failure_types"].items()
        ) or "None"
        lines.append(f"- {summary['label']}: {failures}")

    categories = sorted(
        {
            category
            for summary in summaries
            for category in summary["by_category"]
        }
    )
    lines.extend(["", "## By category", ""])
    for summary in summaries:
        lines.extend(
            [
                f"### {summary['label']}",
                "",
                "| Category | Completed | Evidence coverage |",
                "| --- | ---: | ---: |",
            ]
        )
        for category in categories:
            category_summary = summary["by_category"].get(category)
            if category_summary is None:
                continue
            lines.append(
                "| {category} | {completed}/{total} ({completion:.1%}) | "
                "{evidence:.1%} |".format(
                    category=category,
                    completed=category_summary["completed_cases"],
                    total=category_summary["total_cases"],
                    completion=category_summary["completion_rate"],
                    evidence=category_summary["evidence_coverage"],
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "- `Evidence` includes failed cases as zero coverage, so it reflects end-to-end reliability.",
            "- `Completed evidence` only measures answers that completed successfully.",
            "- Literal path/symbol matching is deterministic and reproducible, but cannot judge whether an explanation is logically correct.",
            "- Final correctness and unsupported-claim counts require human review.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_report(
    cases_path: Path,
    result_paths: dict[str, Path],
    output_path: Path,
    repository: str | None = None,
) -> list[EvaluationSummary]:
    all_cases = load_evaluation_cases(cases_path)
    all_case_ids = {case["case_id"] for case in all_cases}
    cases = [
        case
        for case in all_cases
        if repository is None or case["repository"] == repository
    ]
    selected_case_ids = {case["case_id"] for case in cases}
    summaries = []
    for label, result_path in result_paths.items():
        results = load_evaluation_results(result_path)
        unknown_case_ids = {
            result["case_id"] for result in results
        } - all_case_ids
        if unknown_case_ids:
            names = ", ".join(sorted(unknown_case_ids))
            raise EvaluationScoreError(f"unknown evaluation result case_id: {names}")
        results = [
            result
            for result in results
            if result["case_id"] in selected_case_ids
        ]
        scores = score_evaluation(cases=cases, results=results)
        summaries.append(summarize_scores(label=label, scores=scores))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(summaries), encoding="utf-8")
    return summaries


def _parse_result_argument(value: str) -> tuple[str, Path]:
    label, separator, raw_path = value.partition("=")
    if not separator or not label.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("result must use LABEL=PATH")
    return label.strip(), Path(raw_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score saved Repo Agent results without calling a model.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=EVALUATION_DIR / "data" / "cases.jsonl",
    )
    parser.add_argument(
        "--result",
        action="append",
        type=_parse_result_argument,
        help="repeatable LABEL=PATH result input",
    )
    parser.add_argument(
        "--repository",
        choices=["repo_agent", "pytest", "django"],
        help="score only cases for one repository",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVALUATION_DIR / "reports" / "baseline-summary.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_items = args.result or [
        (
            "Flash High",
            EVALUATION_DIR / "results" / "baseline-flash-high.jsonl",
        ),
        (
            "Pro High",
            EVALUATION_DIR / "results" / "baseline-pro-high.jsonl",
        ),
    ]
    result_paths = dict(cast(list[tuple[str, Path]], result_items))
    if len(result_paths) != len(result_items):
        raise EvaluationScoreError("result labels must be unique")

    summaries = generate_report(
        cases_path=args.cases,
        result_paths=result_paths,
        output_path=args.output,
        repository=args.repository,
    )
    print(f"Scored {len(summaries)} runs. Report: {args.output}")
    print("No model request was sent.")


if __name__ == "__main__":
    main()
