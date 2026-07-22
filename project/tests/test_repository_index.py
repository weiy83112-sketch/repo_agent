import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from repo_agent.retrieval import CodeChunk
from repo_agent.retrieval.chunker import PythonAstChunker
from repo_agent.retrieval.index import (
    IndexVersionError,
    RepositoryIndex,
    RepositoryIndexWarning,
    default_index_path,
)
from repo_agent.retrieval.scanner import RepositoryScanner


def update_index(index: RepositoryIndex, repo_path: Path):
    return index.update(
        repo_path=repo_path,
        scanner=RepositoryScanner(),
        chunker=PythonAstChunker(),
    )


def test_initial_update_persists_files_chunks_and_keyword_search(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "agent.py").write_text(
        "def run_graph_agent():\n    return 'answer'\n",
        encoding="utf-8",
    )

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        summary = update_index(index, repo_path)

        assert summary.added_files == 1
        assert summary.indexed_chunks == 1
        assert list(index.files()) == ["agent.py"]
        chunks = index.chunks("agent.py")
        assert [chunk.symbol_name for chunk in chunks] == ["run_graph_agent"]
        assert index.get_chunk(chunks[0].chunk_id) == chunks[0]
        assert [
            chunk.symbol_name
            for chunk in index.search_keyword("run_graph_agent")
        ] == ["run_graph_agent"]


def test_unchanged_files_are_not_chunked_again(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    class CountingChunker(PythonAstChunker):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def chunk(self, relative_path: str, source: str) -> list[CodeChunk]:
            self.calls.append(relative_path)
            return super().chunk(relative_path, source)

    chunker = CountingChunker()
    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        index.update(repo_path, RepositoryScanner(), chunker)
        second_summary = index.update(repo_path, RepositoryScanner(), chunker)

    assert chunker.calls == ["module.py"]
    assert second_summary.unchanged_files == 1
    assert second_summary.indexed_chunks == 0


def test_modified_file_replaces_old_chunks_and_fts_entries(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    source_path = repo_path / "module.py"
    source_path.write_text("def old_name():\n    return 1\n", encoding="utf-8")

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path)
        source_path.write_text("def new_name():\n    return 2\n", encoding="utf-8")
        summary = update_index(index, repo_path)

        assert summary.modified_files == 1
        assert index.search_keyword("old_name") == []
        assert [chunk.symbol_name for chunk in index.search_keyword("new_name")] == [
            "new_name"
        ]
        assert [chunk.symbol_name for chunk in index.chunks()] == ["new_name"]


def test_deleted_file_removes_chunks_and_fts_entries(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    source_path = repo_path / "removed.py"
    source_path.write_text("def removed_symbol():\n    return 1\n", encoding="utf-8")

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path)
        source_path.unlink()
        summary = update_index(index, repo_path)

        assert summary.deleted_files == 1
        assert index.files() == {}
        assert index.chunks() == []
        assert index.search_keyword("removed_symbol") == []


def test_invalid_python_is_recorded_without_searchable_chunks(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        with pytest.warns(RepositoryIndexWarning, match="without chunks"):
            summary = update_index(index, repo_path)

        assert summary.skipped_files == ("broken.py",)
        assert list(index.files()) == ["broken.py"]
        assert index.chunks() == []


def test_failed_transaction_preserves_previous_complete_index(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "stable.py").write_text("STABLE = True\n", encoding="utf-8")

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path)
        original_files = index.files()
        original_chunks = index.chunks()

        (repo_path / "first.py").write_text("FIRST = 1\n", encoding="utf-8")
        (repo_path / "second.py").write_text("SECOND = 2\n", encoding="utf-8")

        class DuplicateIdChunker(PythonAstChunker):
            def chunk(self, relative_path: str, source: str) -> list[CodeChunk]:
                chunks = super().chunk(relative_path, source)
                return [replace(chunk, chunk_id="duplicate-id") for chunk in chunks]

        with pytest.raises(sqlite3.IntegrityError):
            index.update(repo_path, RepositoryScanner(), DuplicateIdChunker())

        assert index.files() == original_files
        assert index.chunks() == original_chunks


def test_incompatible_schema_version_is_rejected(tmp_path: Path) -> None:
    index_path = tmp_path / "index.sqlite3"
    connection = sqlite3.connect(index_path)
    connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)")
    connection.execute(
        "INSERT INTO metadata(key, value) VALUES ('schema_version', '999')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(IndexVersionError, match="schema version 999"):
        RepositoryIndex(index_path)


def test_default_index_path_is_stable_and_outside_repository(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    first = default_index_path(repo_path)
    second = default_index_path(repo_path)

    assert first == second
    assert first.name == "index.sqlite3"
    assert not first.is_relative_to(repo_path.resolve())


def test_keyword_search_handles_empty_and_punctuated_queries(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "router.py").write_text(
        "class ModelRouter:\n"
        "    def complex(self):\n"
        "        return None\n",
        encoding="utf-8",
    )

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path)

        assert index.search_keyword("---") == []
        results = index.search_keyword("ModelRouter.complex()")
        assert results
        assert results[0].symbol_name == "ModelRouter.complex"


def test_keyword_search_prefers_exact_symbol_over_similar_symbol(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "functions.py").write_text(
        "def fake_run_graph_agent():\n"
        "    return None\n"
        "\n"
        "def run_graph_agent():\n"
        "    return None\n",
        encoding="utf-8",
    )

    with RepositoryIndex(tmp_path / "index.sqlite3") as index:
        update_index(index, repo_path)
        results = index.search_keyword("run_graph_agent")

    assert results[0].symbol_name == "run_graph_agent"
