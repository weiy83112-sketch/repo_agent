import importlib
import sys
from types import SimpleNamespace

from evaluation.adapters import BaselineAgentAdapter, HybridRagAgentAdapter
from repo_agent.model_router import ModelRouter


evaluation_cli = importlib.import_module("evaluation.__main__")


def test_parse_args_defaults_to_baseline(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluation", "--capability", "simple", "--validate-only"],
    )

    args = evaluation_cli.parse_args()

    assert args.stage == "baseline"
    assert args.capability == "simple"
    assert args.validate_only is True
    assert args.repository is None


def test_parse_args_selects_hybrid_rag(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluation",
            "--stage",
            "hybrid-rag",
            "--capability",
            "complex",
            "--repository",
            "pytest",
        ],
    )

    args = evaluation_cli.parse_args()

    assert args.stage == "hybrid-rag"
    assert args.capability == "complex"
    assert args.repository == "pytest"


def test_stage_selects_adapter_without_changing_runner() -> None:
    router = ModelRouter(client=SimpleNamespace())
    baseline = evaluation_cli.create_evaluation_agent(
        stage="baseline",
        router=router,
        capability="simple",
    )
    hybrid = evaluation_cli.create_evaluation_agent(
        stage="hybrid-rag",
        router=router,
        capability="simple",
    )

    try:
        assert isinstance(baseline, BaselineAgentAdapter)
        assert isinstance(hybrid, HybridRagAgentAdapter)
        assert evaluation_cli.OUTPUT_NAMES["baseline"]["simple"] == (
            "baseline-flash-high.jsonl"
        )
        assert evaluation_cli.OUTPUT_NAMES["hybrid-rag"]["simple"] == (
            "hybrid-rag-flash-high.jsonl"
        )
    finally:
        evaluation_cli.close_evaluation_agent(baseline)
        evaluation_cli.close_evaluation_agent(hybrid)


def test_repository_filter_uses_a_separate_result_name() -> None:
    assert evaluation_cli.result_output_name(
        "hybrid-rag",
        "simple",
        "pytest",
    ) == "hybrid-rag-flash-high-pytest.jsonl"
    assert evaluation_cli.result_output_name(
        "baseline",
        "complex",
        None,
    ) == "baseline-pro-high.jsonl"
