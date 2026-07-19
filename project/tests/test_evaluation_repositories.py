import json
from pathlib import Path

import pytest

import evaluation.repositories as repositories
from evaluation.repositories import RepositoryDataError, load_repository_paths


def write_repositories(path: Path, commit: str = "abc123") -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "name": "sample",
                    "url": "https://example.com/sample.git",
                    "commit": commit,
                    "local_path": "source/sample",
                }
            ]
        ),
        encoding="utf-8",
    )


def test_repository_loader_resolves_paths_and_verifies_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "repositories.json"
    sample_repo = tmp_path / "source" / "sample"
    sample_repo.mkdir(parents=True)
    own_repo = tmp_path / "project"
    own_repo.mkdir()
    write_repositories(snapshot_path)
    monkeypatch.setattr(repositories, "_read_git_commit", lambda path: "abc123")

    repo_paths = load_repository_paths(
        path=snapshot_path,
        workspace_root=tmp_path,
        extra_repo_paths={"repo_agent": own_repo},
    )

    assert repo_paths == {
        "sample": sample_repo.resolve(),
        "repo_agent": own_repo.resolve(),
    }


def test_repository_loader_rejects_wrong_commit(tmp_path: Path, monkeypatch) -> None:
    snapshot_path = tmp_path / "repositories.json"
    (tmp_path / "source" / "sample").mkdir(parents=True)
    write_repositories(snapshot_path, commit="expected")
    monkeypatch.setattr(repositories, "_read_git_commit", lambda path: "actual")

    with pytest.raises(RepositoryDataError, match="commit mismatch"):
        load_repository_paths(path=snapshot_path, workspace_root=tmp_path)
