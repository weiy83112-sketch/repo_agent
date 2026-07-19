import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from evaluation.adapters import EvaluationAgent
from evaluation.schemas import EvaluationCase
from repo_agent.exceptions import AgentLimitError, AgentResponseError, AgentTimeoutError
from repo_agent.model_router import ModelMetadata


class EvaluationResultError(ValueError):
    """已有结果文件与本轮评测不兼容或格式损坏。"""


def _load_saved_case_ids(
    output_path: Path,
    case_repositories: dict[str, str],
    stage: str,
    metadata: ModelMetadata,
) -> set[str]:
    if not output_path.exists():
        return set()

    saved_case_ids: set[str] = set()
    required_fields = {
        "case_id",
        "stage",
        "repository",
        "capability",
        "model",
        "thinking",
        "reasoning_effort",
        "answer",
        "tool_calls",
        "elapsed_seconds",
        "status",
        "error_type",
        "error_message",
    }
    expected_metadata = {
        "stage": stage,
        "capability": metadata.capability,
        "model": metadata.model,
        "thinking": metadata.thinking,
        "reasoning_effort": metadata.reasoning_effort,
    }

    with output_path.open("r", encoding="utf-8") as output_file:
        for line_number, raw_line in enumerate(output_file, start=1):
            try:
                result = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: invalid result JSON"
                ) from error

            if not isinstance(result, dict):
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: result must be an object"
                )

            missing_fields = required_fields - result.keys()
            if missing_fields:
                names = ", ".join(sorted(missing_fields))
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: missing result fields: {names}"
                )

            case_id = result["case_id"]
            if case_id not in case_repositories:
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: unknown case_id: {case_id}"
                )
            if case_id in saved_case_ids:
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: duplicate case_id: {case_id}"
                )

            for field, expected_value in expected_metadata.items():
                if result.get(field) != expected_value:
                    raise EvaluationResultError(
                        f"{output_path}:{line_number}: {field} does not match this run"
                    )

            if result["repository"] != case_repositories[case_id]:
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: repository does not match case"
                )
            if not isinstance(result["tool_calls"], list):
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: tool_calls must be a list"
                )
            if (
                not isinstance(result["elapsed_seconds"], (int, float))
                or isinstance(result["elapsed_seconds"], bool)
                or result["elapsed_seconds"] < 0
            ):
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: elapsed_seconds must be non-negative"
                )

            status = result["status"]
            if status not in {"completed", "failed"}:
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: invalid result status"
                )
            if status == "completed" and (
                not isinstance(result["answer"], str)
                or not result["answer"].strip()
                or result["error_type"] is not None
                or result["error_message"] is not None
            ):
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: invalid completed result"
                )
            if status == "failed" and (
                result["answer"] is not None
                or not isinstance(result["error_type"], str)
                or not result["error_type"].strip()
                or not isinstance(result["error_message"], str)
            ):
                raise EvaluationResultError(
                    f"{output_path}:{line_number}: invalid failed result"
                )

            saved_case_ids.add(case_id)

    return saved_case_ids


def validate_evaluation_run(
    cases: list[EvaluationCase],
    repo_paths: dict[str, Path],
    agent: EvaluationAgent,
    stage: str,
    output_path: Path,
) -> set[str]:
    """在模型调用前验证题库映射、Adapter 元数据和断点结果文件。"""

    # 在第一次付费调用之前检查全部仓库映射，避免跑到一半才发现配置错误。
    for case in cases:
        repository = case["repository"]
        if repository not in repo_paths:
            raise ValueError(f"repository is not configured: {repository}")
        if not repo_paths[repository].is_dir():
            raise ValueError(f"repository path does not exist: {repo_paths[repository]}")

    metadata = agent.model_metadata
    case_repositories = {
        case["case_id"]: case["repository"]
        for case in cases
    }
    if len(case_repositories) != len(cases):
        raise ValueError("evaluation cases contain duplicate case_id values")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    saved_case_ids = _load_saved_case_ids(
        output_path=output_path,
        case_repositories=case_repositories,
        stage=stage,
        metadata=metadata,
    )

    # 以追加模式打开并立即关闭，提前确认结果路径可创建、可写入。
    with output_path.open("a", encoding="utf-8"):
        pass

    return saved_case_ids


def run_evaluation(
    cases: list[EvaluationCase],
    repo_paths: dict[str, Path],
    agent: EvaluationAgent,
    stage: str,
    output_path: Path,
    on_result: Callable[[dict], None] | None = None,
) -> None:
    """按题库顺序运行统一 Agent 接口，并逐题追加 JSONL 结果。"""

    metadata = agent.model_metadata
    saved_case_ids = validate_evaluation_run(
        cases=cases,
        repo_paths=repo_paths,
        agent=agent,
        stage=stage,
        output_path=output_path,
    )

    # 文件在整轮运行期间保持打开；每题 write 后立即 flush，支持中断后续跑。
    with output_path.open("a", encoding="utf-8") as output_file:
        for case in cases:
            if case["case_id"] in saved_case_ids:
                continue

            tool_calls: list[dict] = []

            # 这个内层函数会记住当前题目的 tool_calls 列表。
            def on_tool_call(name: str, arguments: dict) -> None:
                tool_calls.append({"name": name, "arguments": arguments})

            started_at = perf_counter()
            try:
                answer = agent.run(
                    repo_path=repo_paths[case["repository"]],
                    question=case["question"],
                    on_tool_call=on_tool_call,
                )
                status = "completed"
                error_type = None
                error_message = None
            except AgentTimeoutError as error:
                # Timeout 是 AgentLimitError 的子类，所以必须放在父类之前捕获。
                answer = None
                status = "failed"
                error_type = type(error).__name__
                error_message = str(error)
            except (AgentLimitError, AgentResponseError) as error:
                answer = None
                status = "failed"
                error_type = type(error).__name__
                error_message = str(error)

            elapsed_seconds = perf_counter() - started_at

            result = {
                "case_id": case["case_id"],
                "stage": stage,
                "repository": case["repository"],
                "capability": metadata.capability,
                "model": metadata.model,
                "thinking": metadata.thinking,
                "reasoning_effort": metadata.reasoning_effort,
                "answer": answer,
                "tool_calls": tool_calls,
                "elapsed_seconds": elapsed_seconds,
                "status": status,
                "error_type": error_type,
                "error_message": error_message,
            }
            output_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            output_file.flush()

            if on_result is not None:
                on_result(result)
