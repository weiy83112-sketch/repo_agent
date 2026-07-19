import json
import subprocess
from pathlib import Path


class RepositoryDataError(ValueError):
    """仓库快照配置无效，或本地仓库与固定提交不一致。"""


def _read_git_commit(repo_path: Path) -> str:
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={repo_path}",
                "-C",
                str(repo_path),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RepositoryDataError(f"cannot read repository commit: {repo_path}") from error

    return completed.stdout.strip()


def load_repository_paths(
    path: Path,
    workspace_root: Path,
    extra_repo_paths: dict[str, Path] | None = None,
) -> dict[str, Path]:
    """加载并验证固定仓库快照，返回仓库名称到绝对路径的映射。"""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RepositoryDataError(f"{path}: invalid JSON") from error

    if not isinstance(data, list):
        raise RepositoryDataError(f"{path}: repositories must be a list")

    root = workspace_root.resolve()
    repo_paths: dict[str, Path] = {}
    required_keys = {"name", "url", "commit", "local_path"}

    for index, item in enumerate(data, start=1):
        location = f"{path}: repository {index}"
        if not isinstance(item, dict) or set(item) != required_keys:
            raise RepositoryDataError(f"{location}: invalid repository fields")

        if not all(isinstance(item[key], str) and item[key].strip() for key in required_keys):
            raise RepositoryDataError(f"{location}: repository fields must be non-empty strings")

        name = item["name"]
        if name in repo_paths:
            raise RepositoryDataError(f"{location}: duplicate repository name: {name}")

        repo_path = (root / item["local_path"]).resolve()
        if not repo_path.is_relative_to(root):
            raise RepositoryDataError(f"{location}: local_path escapes workspace root")
        if not repo_path.is_dir():
            raise RepositoryDataError(f"{location}: repository path does not exist: {repo_path}")

        actual_commit = _read_git_commit(repo_path)
        if actual_commit != item["commit"]:
            raise RepositoryDataError(
                f"{location}: commit mismatch: expected {item['commit']}, got {actual_commit}"
            )

        repo_paths[name] = repo_path

    for name, extra_path in (extra_repo_paths or {}).items():
        if name in repo_paths:
            raise RepositoryDataError(f"duplicate repository name: {name}")

        resolved_path = extra_path.resolve()
        if not resolved_path.is_dir():
            raise RepositoryDataError(f"repository path does not exist: {resolved_path}")
        repo_paths[name] = resolved_path

    return repo_paths
