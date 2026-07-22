from pathlib import Path

import pytest

from repo_agent.retrieval.chunker import PythonAstChunker, PythonChunkingError


SOURCE = '''"""Module documentation."""
import os

CONSTANT = 1

@decorator
class Service:
    """Service documentation."""

    def run(self):
        """Run the service."""
        return os.getcwd()

    async def stop(self):
        return None


def helper():
    return CONSTANT
'''


def test_chunker_creates_module_class_function_and_method_chunks() -> None:
    chunks = PythonAstChunker().chunk("package/service.py", SOURCE)
    chunks_by_symbol = {
        (chunk.symbol_name, chunk.kind): chunk
        for chunk in chunks
    }

    assert ("<module>", "module") in chunks_by_symbol
    assert ("Service", "class") in chunks_by_symbol
    assert ("Service.run", "method") in chunks_by_symbol
    assert ("Service.stop", "method") in chunks_by_symbol
    assert ("helper", "function") in chunks_by_symbol


def test_chunker_preserves_traceable_lines_docstrings_and_decorators() -> None:
    chunks = PythonAstChunker().chunk("package/service.py", SOURCE)
    service = next(chunk for chunk in chunks if chunk.symbol_name == "Service")
    run = next(chunk for chunk in chunks if chunk.symbol_name == "Service.run")

    assert service.file_path == "package/service.py"
    assert service.start_line == 6
    assert service.code.startswith("@decorator\nclass Service:")
    assert service.docstring == "Service documentation."
    assert run.parent_symbol == "Service"
    assert run.docstring == "Run the service."
    assert SOURCE.splitlines()[run.start_line - 1].strip() == "def run(self):"
    assert SOURCE.splitlines()[run.end_line - 1].strip() == "return os.getcwd()"


def test_chunk_id_is_stable_when_only_source_lines_move() -> None:
    chunker = PythonAstChunker()
    original = chunker.chunk("module.py", "def run():\n    return 1\n")[0]
    moved = chunker.chunk("module.py", "\n\n\ndef run():\n    return 1\n")[0]

    assert original.chunk_id == moved.chunk_id
    assert original.content_hash == moved.content_hash
    assert original.start_line != moved.start_line


def test_content_hash_changes_without_changing_chunk_identity() -> None:
    chunker = PythonAstChunker()
    original = chunker.chunk("module.py", "def run():\n    return 1\n")[0]
    changed = chunker.chunk("module.py", "def run():\n    return 2\n")[0]

    assert original.chunk_id == changed.chunk_id
    assert original.content_hash != changed.content_hash


def test_duplicate_symbol_definitions_receive_unique_chunk_ids() -> None:
    chunks = PythonAstChunker().chunk(
        "module.py",
        "def run():\n    return 1\n\ndef run():\n    return 2\n",
    )

    assert [chunk.symbol_name for chunk in chunks] == ["run", "run"]
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_nested_symbols_use_qualified_names() -> None:
    chunks = PythonAstChunker().chunk(
        "module.py",
        "class Outer:\n"
        "    class Inner:\n"
        "        def method(self):\n"
        "            return 1\n"
        "\n"
        "def outer():\n"
        "    def inner():\n"
        "        return 2\n"
        "    return inner()\n",
    )

    assert [chunk.symbol_name for chunk in chunks] == [
        "Outer",
        "Outer.Inner",
        "Outer.Inner.method",
        "outer",
        "outer.inner",
    ]
    inner_function = chunks[-1]
    assert inner_function.kind == "function"
    assert inner_function.parent_symbol == "outer"


def test_chunker_reports_invalid_python_with_file_location() -> None:
    with pytest.raises(
        PythonChunkingError,
        match=r"broken\.py:1: invalid Python syntax",
    ):
        PythonAstChunker().chunk("broken.py", "def broken(:\n")
