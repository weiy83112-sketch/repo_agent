import os
import warnings
from hashlib import sha256
from pathlib import Path

from .models import ScannedFile


DEFAULT_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "env",
        "node_modules",
        "site-packages",
        "venv",
    }
)


class RepositoryScanWarning(UserWarning):
    """A source file was safely skipped while scanning a repository."""


class RepositoryScanner:
    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        excluded_directories: frozenset[str] = DEFAULT_EXCLUDED_DIRECTORIES,
    ) -> None:
        if max_file_size_bytes < 1:
            raise ValueError("max_file_size_bytes must be positive")

        self._max_file_size_bytes = max_file_size_bytes
        self._excluded_directories = excluded_directories

    def scan(self, repo_path: Path) -> list[ScannedFile]:
        repo_root = repo_path.resolve()
        if not repo_root.is_dir():
            raise ValueError(f"repository path is not a directory: {repo_path}")

        scanned_files: list[ScannedFile] = []

        for current_root, directory_names, file_names in os.walk(
            repo_root,
            topdown=True,
            followlinks=False,
        ):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name not in self._excluded_directories
                and not (Path(current_root) / name).is_symlink()
            )

            for file_name in sorted(file_names):
                if not file_name.endswith(".py"):
                    continue

                file_path = Path(current_root) / file_name
                if file_path.is_symlink():
                    self._warn(file_path, "symbolic links are not indexed")
                    continue

                resolved_path = file_path.resolve()
                if not resolved_path.is_relative_to(repo_root):
                    self._warn(file_path, "path leaves the repository")
                    continue

                try:
                    file_stat = resolved_path.stat()
                    if file_stat.st_size > self._max_file_size_bytes:
                        self._warn(file_path, "file is too large")
                        continue

                    content = resolved_path.read_bytes()
                    content.decode("utf-8")
                except UnicodeDecodeError:
                    self._warn(file_path, "file is not valid UTF-8")
                    continue
                except OSError as error:
                    self._warn(file_path, str(error))
                    continue

                relative_path = resolved_path.relative_to(repo_root).as_posix()
                scanned_files.append(
                    ScannedFile(
                        relative_path=relative_path,
                        size_bytes=len(content),
                        modified_ns=file_stat.st_mtime_ns,
                        content_hash=sha256(content).hexdigest(),
                    )
                )

        scanned_files.sort(key=lambda item: item.relative_path)
        return scanned_files

    @staticmethod
    def _warn(file_path: Path, reason: str) -> None:
        warnings.warn(
            f"skipping {file_path}: {reason}",
            RepositoryScanWarning,
            stacklevel=2,
        )
