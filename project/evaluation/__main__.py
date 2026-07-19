import argparse
from pathlib import Path

from evaluation.adapters import BaselineAgentAdapter
from evaluation.loader import load_evaluation_cases, validate_evaluation_evidence
from evaluation.repositories import load_repository_paths
from evaluation.runner import run_evaluation, validate_evaluation_run
from repo_agent.model_router import ModelCapability, ModelRouter


PROJECT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_DIR.parent
EVALUATION_DIR = PROJECT_DIR / "evaluation"

OUTPUT_NAMES: dict[ModelCapability, str] = {
    "simple": "baseline-flash-high.jsonl",
    "complex": "baseline-pro-high.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fixed Repo Agent baseline evaluation.",
    )
    parser.add_argument(
        "--capability",
        choices=["simple", "complex"],
        required=True,
        help="simple uses Flash High; complex uses Pro High",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate cases and repository snapshots without calling a model",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    capability: ModelCapability = args.capability

    cases = load_evaluation_cases(EVALUATION_DIR / "data" / "cases.jsonl")
    repo_paths = load_repository_paths(
        path=EVALUATION_DIR / "data" / "repositories.json",
        workspace_root=WORKSPACE_ROOT,
        extra_repo_paths={"repo_agent": PROJECT_DIR},
    )

    repositories_used = {case["repository"] for case in cases}
    missing_repositories = repositories_used - repo_paths.keys()
    if missing_repositories:
        names = ", ".join(sorted(missing_repositories))
        raise ValueError(f"evaluation repositories are not configured: {names}")

    validate_evaluation_evidence(cases=cases, repo_paths=repo_paths)

    router = ModelRouter()
    agent = BaselineAgentAdapter(
        router=router,
        capability=capability,
        max_graph_steps=20,
    )
    metadata = agent.model_metadata
    output_path = EVALUATION_DIR / "results" / OUTPUT_NAMES[capability]

    if args.validate_only:
        saved_case_ids = validate_evaluation_run(
            cases=cases,
            repo_paths=repo_paths,
            agent=agent,
            stage="baseline",
            output_path=output_path,
        )
        print(
            f"Validated {len(cases)} cases across "
            f"{len(repositories_used)} repositories; "
            f"{len(saved_case_ids)} saved results are resumable.",
            flush=True,
        )
        print("Validation only: no model request was sent.", flush=True)
        return

    print(
        f"Running {metadata.model} with thinking={metadata.thinking}, "
        f"reasoning_effort={metadata.reasoning_effort}.",
        flush=True,
    )

    def print_result(result: dict) -> None:
        print(
            f"[{result['status']}] {result['case_id']} "
            f"({result['elapsed_seconds']:.2f}s)",
            flush=True,
        )

    run_evaluation(
        cases=cases,
        repo_paths=repo_paths,
        agent=agent,
        stage="baseline",
        output_path=output_path,
        on_result=print_result,
    )
    print(f"Results: {output_path}", flush=True)


if __name__ == "__main__":
    main()
