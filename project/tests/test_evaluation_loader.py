import json
from pathlib import Path

import pytest

from evaluation import (
    EvaluationDataError,
    load_evaluation_cases,
    validate_evaluation_evidence,
)


def write_cases(path: Path, cases: list[dict]) -> None:
    lines = [json.dumps(case, ensure_ascii=False) for case in cases]
    path.write_text("\n".join(lines), encoding="utf-8")


def test_loader_accepts_non_empty_case_id(tmp_path: Path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    write_cases(
        cases_path,
        [
            {
                "case_id": "pytest-entry-001",
                "repository": "pytest",
                "question": "pytest 的入口在哪里？",
                "expected_files": ["src/pytest/__main__.py"],
                "expected_symbols": ["_console_main"],
                "category": "entry_point",
            }
        ],
    )

    cases = load_evaluation_cases(cases_path)

    assert cases[0]["case_id"] == "pytest-entry-001"


def test_loader_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    first_case = {
        "case_id": "pytest-entry-001",
        "repository": "pytest",
        "question": "pytest 的入口在哪里？",
        "expected_files": ["src/pytest/__main__.py"],
        "expected_symbols": ["_console_main"],
        "category": "entry_point",
    }
    second_case = {
        **first_case,
        "question": "另一个错误使用了相同 ID 的问题",
    }
    write_cases(cases_path, [first_case, second_case])

    with pytest.raises(EvaluationDataError, match="duplicate case_id"):
        load_evaluation_cases(cases_path)


def test_evidence_validation_rejects_missing_symbol(tmp_path: Path) -> None:
    repo_path = tmp_path / "sample"
    repo_path.mkdir()
    (repo_path / "sample.py").write_text("def existing():\n    pass\n", encoding="utf-8")
    case = {
        "case_id": "sample-feature-001",
        "repository": "sample",
        "question": "Where is missing_symbol?",
        "expected_files": ["sample.py"],
        "expected_symbols": ["missing_symbol"],
        "category": "feature_location",
    }

    with pytest.raises(EvaluationDataError, match="expected symbol not found"):
        validate_evaluation_evidence(
            cases=[case],
            repo_paths={"sample": repo_path},
        )
