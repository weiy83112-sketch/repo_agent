from dataclasses import dataclass
from math import isfinite
from typing import Literal


ChunkKind = Literal["module", "class", "function", "method"]
RetrievalSource = Literal["keyword", "vector"]


@dataclass(frozen=True, slots=True)
class ScannedFile:
    """Repository-relative metadata used to detect source-file changes."""

    relative_path: str
    size_bytes: int
    modified_ns: int
    content_hash: str

    def __post_init__(self) -> None:
        if not self.relative_path:
            raise ValueError("relative_path must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")
        if self.modified_ns < 0:
            raise ValueError("modified_ns must not be negative")
        if not self.content_hash:
            raise ValueError("content_hash must not be empty")


@dataclass(frozen=True, slots=True)
class FileChanges:
    """The file-level difference between a scan and the stored index."""

    added: tuple[ScannedFile, ...]
    modified: tuple[ScannedFile, ...]
    unchanged: tuple[ScannedFile, ...]
    deleted: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexUpdateSummary:
    """Counts and warnings produced by one atomic repository-index update."""

    added_files: int
    modified_files: int
    unchanged_files: int
    deleted_files: int
    indexed_chunks: int
    embedded_chunks: int
    skipped_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """A stable, repository-relative unit of Python source code."""

    chunk_id: str
    file_path: str
    symbol_name: str
    kind: ChunkKind
    start_line: int
    end_line: int
    code: str
    docstring: str | None
    parent_symbol: str | None
    content_hash: str

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raise ValueError("chunk_id must not be empty")
        if not self.file_path:
            raise ValueError("file_path must not be empty")
        if not self.symbol_name:
            raise ValueError("symbol_name must not be empty")
        if self.kind not in {"module", "class", "function", "method"}:
            raise ValueError(f"unsupported chunk kind: {self.kind}")
        if self.start_line < 1:
            raise ValueError("start_line must be at least 1")
        if self.end_line < self.start_line:
            raise ValueError("end_line must not be before start_line")
        if not self.code:
            raise ValueError("code must not be empty")
        if not self.content_hash:
            raise ValueError("content_hash must not be empty")


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A code chunk annotated with ranking data for one retrieval request."""

    chunk: CodeChunk
    score: float
    sources: tuple[RetrievalSource, ...]
    keyword_rank: int | None = None
    vector_rank: int | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.score) or self.score < 0:
            raise ValueError("score must be a finite non-negative number")
        if not self.sources:
            raise ValueError("sources must not be empty")
        if len(set(self.sources)) != len(self.sources):
            raise ValueError("sources must not contain duplicates")
        invalid_sources = set(self.sources) - {"keyword", "vector"}
        if invalid_sources:
            names = ", ".join(sorted(invalid_sources))
            raise ValueError(f"unsupported retrieval sources: {names}")

        if "keyword" in self.sources:
            self._validate_rank("keyword_rank", self.keyword_rank)
        elif self.keyword_rank is not None:
            raise ValueError("keyword_rank requires the keyword source")

        if "vector" in self.sources:
            self._validate_rank("vector_rank", self.vector_rank)
        elif self.vector_rank is not None:
            raise ValueError("vector_rank requires the vector source")

    @staticmethod
    def _validate_rank(name: str, value: int | None) -> None:
        if value is None or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
