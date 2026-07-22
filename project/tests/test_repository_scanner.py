from hashlib import sha256
from pathlib import Path

import pytest

from repo_agent.retrieval.scanner import RepositoryScanner, RepositoryScanWarning


def test_scanner_returns_sorted_python_file_metadata(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    second_content = b"def second():\n    return 2\n"
    (package / "second.py").write_bytes(second_content)
    (tmp_path / "first.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("ignored", encoding="utf-8")

    files = RepositoryScanner().scan(tmp_path)

    assert [file.relative_path for file in files] == [
        "first.py",
        "package/second.py",
    ]
    assert files[1].size_bytes == len(second_content)
    assert files[1].content_hash == sha256(second_content).hexdigest()
    assert files[1].modified_ns > 0


def test_scanner_prunes_excluded_directories(tmp_path: Path) -> None:
    (tmp_path / "visible.py").write_text("VISIBLE = True\n", encoding="utf-8")
    for directory_name in (".git", ".venv", "__pycache__", "build"):
        directory = tmp_path / directory_name
        directory.mkdir()
        (directory / "hidden.py").write_text("HIDDEN = True\n", encoding="utf-8")

    files = RepositoryScanner().scan(tmp_path)

    assert [file.relative_path for file in files] == ["visible.py"]


def test_scanner_skips_oversized_and_invalid_utf8_files(tmp_path: Path) -> None:
    (tmp_path / "valid.py").write_text("OK = True\n", encoding="utf-8")
    (tmp_path / "large.py").write_text("0123456789", encoding="utf-8")
    (tmp_path / "binary.py").write_bytes(b"\xff\xfe")

    scanner = RepositoryScanner(max_file_size_bytes=9)
    with pytest.warns(RepositoryScanWarning) as recorded:
        files = scanner.scan(tmp_path)

    assert [file.relative_path for file in files] == []
    messages = [str(item.message) for item in recorded]
    assert any("file is too large" in message for message in messages)
    assert any("valid UTF-8" in message for message in messages)


def test_scanner_content_hash_changes_with_file_content(tmp_path: Path) -> None:
    source_path = tmp_path / "module.py"
    source_path.write_text("VALUE = 1\n", encoding="utf-8")
    original = RepositoryScanner().scan(tmp_path)[0]

    source_path.write_text("VALUE = 2\n", encoding="utf-8")
    changed = RepositoryScanner().scan(tmp_path)[0]

    assert original.relative_path == changed.relative_path
    assert original.content_hash != changed.content_hash


def test_scanner_rejects_missing_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository path is not a directory"):
        RepositoryScanner().scan(tmp_path / "missing")
