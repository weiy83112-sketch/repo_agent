import json
from pathlib import Path

import pytest

from evaluation.runner import EvaluationResultError, run_evaluation
from repo_agent.exceptions import AgentLimitError, AgentResponseError, AgentTimeoutError
from repo_agent.model_router import ModelMetadata


def make_case(case_id: str, repository: str = "sample") -> dict:
    return {
        "case_id": case_id,
        "repository": repository,
        "question": f"question for {case_id}",
        "expected_files": ["sample.py"],
        "expected_symbols": [],
        "category": "feature_location",
    }


class FakeAgent:
    model_metadata = ModelMetadata(
        capability="simple",
        model="deepseek-v4-flash",
        thinking="enabled",
        reasoning_effort="high",
    )

    def __init__(self) -> None:
        self.case_ids: list[str] = []

    def run(self, repo_path: Path, question: str, on_tool_call) -> str:
        case_id = question.removeprefix("question for ")
        self.case_ids.append(case_id)
        on_tool_call("read_file", {"path": "sample.py"})
        return f"answer for {case_id}"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_runner_records_successful_cases_in_order(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "results" / "baseline-flash-high.jsonl"
    agent = FakeAgent()

    run_evaluation(
        cases=[make_case("case-001"), make_case("case-002")],
        repo_paths={"sample": repo_path},
        agent=agent,
        stage="baseline",
        output_path=output_path,
    )

    results = read_jsonl(output_path)
    assert agent.case_ids == ["case-001", "case-002"]
    assert [result["case_id"] for result in results] == ["case-001", "case-002"]
    assert results[0]["status"] == "completed"
    assert results[0]["answer"] == "answer for case-001"
    assert results[0]["tool_calls"] == [
        {"name": "read_file", "arguments": {"path": "sample.py"}}
    ]
    assert results[0]["capability"] == "simple"
    assert results[0]["model"] == "deepseek-v4-flash"
    assert results[0]["thinking"] == "enabled"
    assert results[0]["reasoning_effort"] == "high"
    assert results[0]["error_type"] is None
    assert results[0]["error_message"] is None
    assert isinstance(results[0]["elapsed_seconds"], float)


def test_runner_skips_case_ids_already_saved(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "baseline-flash-high.jsonl"
    cases = [make_case("case-001"), make_case("case-002")]

    first_agent = FakeAgent()
    run_evaluation(
        cases=cases,
        repo_paths={"sample": repo_path},
        agent=first_agent,
        stage="baseline",
        output_path=output_path,
    )

    resumed_agent = FakeAgent()
    run_evaluation(
        cases=cases,
        repo_paths={"sample": repo_path},
        agent=resumed_agent,
        stage="baseline",
        output_path=output_path,
    )

    assert resumed_agent.case_ids == []
    assert [result["case_id"] for result in read_jsonl(output_path)] == [
        "case-001",
        "case-002",
    ]


class FailingAgent(FakeAgent):
    def run(self, repo_path: Path, question: str, on_tool_call) -> str:
        case_id = question.removeprefix("question for ")
        self.case_ids.append(case_id)

        if case_id == "timeout":
            raise AgentTimeoutError("request timed out")
        if case_id == "limit":
            raise AgentLimitError("too many graph steps")
        if case_id == "no-text":
            raise AgentResponseError("final answer has no text")

        return "recovered"


def test_runner_records_agent_failures_and_continues(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "results.jsonl"
    agent = FailingAgent()

    run_evaluation(
        cases=[
            make_case("timeout"),
            make_case("limit"),
            make_case("no-text"),
            make_case("success"),
        ],
        repo_paths={"sample": repo_path},
        agent=agent,
        stage="baseline",
        output_path=output_path,
    )

    results = read_jsonl(output_path)
    assert agent.case_ids == ["timeout", "limit", "no-text", "success"]
    assert [result["status"] for result in results] == [
        "failed",
        "failed",
        "failed",
        "completed",
    ]
    assert [result["error_type"] for result in results] == [
        "AgentTimeoutError",
        "AgentLimitError",
        "AgentResponseError",
        None,
    ]
    assert results[0]["answer"] is None


class GlobalFailureAgent(FakeAgent):
    def run(self, repo_path: Path, question: str, on_tool_call) -> str:
        case_id = question.removeprefix("question for ")
        self.case_ids.append(case_id)
        if case_id == "global-error":
            raise RuntimeError("invalid API configuration")
        return "saved before global failure"


def test_runner_stops_on_global_failure_and_keeps_saved_results(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "results.jsonl"
    agent = GlobalFailureAgent()

    with pytest.raises(RuntimeError, match="invalid API configuration"):
        run_evaluation(
            cases=[
                make_case("completed-first"),
                make_case("global-error"),
                make_case("must-not-run"),
            ],
            repo_paths={"sample": repo_path},
            agent=agent,
            stage="baseline",
            output_path=output_path,
        )

    assert agent.case_ids == ["completed-first", "global-error"]
    assert [result["case_id"] for result in read_jsonl(output_path)] == [
        "completed-first"
    ]


def test_runner_rejects_mixed_model_results_before_agent_call(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "results.jsonl"
    output_path.write_text(
        json.dumps(
                {
                    "case_id": "case-001",
                    "stage": "baseline",
                    "repository": "sample",
                    "capability": "complex",
                    "model": "deepseek-v4-pro",
                    "thinking": "enabled",
                    "reasoning_effort": "high",
                    "answer": "answer from the wrong model",
                    "tool_calls": [],
                    "elapsed_seconds": 1.0,
                    "status": "completed",
                    "error_type": None,
                    "error_message": None,
                }
        )
        + "\n",
        encoding="utf-8",
    )
    agent = FakeAgent()

    with pytest.raises(EvaluationResultError, match="capability does not match"):
        run_evaluation(
            cases=[make_case("case-001")],
            repo_paths={"sample": repo_path},
            agent=agent,
            stage="baseline",
            output_path=output_path,
        )

    assert agent.case_ids == []


def test_runner_rejects_incomplete_saved_result(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    output_path = tmp_path / "results.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "case_id": "case-001",
                "stage": "baseline",
                "repository": "sample",
                "capability": "simple",
                "model": "deepseek-v4-flash",
                "thinking": "enabled",
                "reasoning_effort": "high",
                "status": "completed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    agent = FakeAgent()

    with pytest.raises(EvaluationResultError, match="missing result fields"):
        run_evaluation(
            cases=[make_case("case-001")],
            repo_paths={"sample": repo_path},
            agent=agent,
            stage="baseline",
            output_path=output_path,
        )

    assert agent.case_ids == []
