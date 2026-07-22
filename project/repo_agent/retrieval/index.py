import os
import re
import sqlite3
import warnings
from hashlib import sha256
from pathlib import Path
from types import TracebackType

import numpy as np

from .chunker import PythonAstChunker, PythonChunkingError
from .embedder import Embedder, EmbeddingError, code_chunk_embedding_text
from .models import CodeChunk, FileChanges, IndexUpdateSummary, ScannedFile
from .scanner import RepositoryScanner


SCHEMA_VERSION = 1


class IndexVersionError(RuntimeError):
    """An existing repository index uses an incompatible schema version."""


class RepositoryIndexWarning(UserWarning):
    """A source file could not be indexed but the repository update continued."""


class EmbeddingProfileError(RuntimeError):
    """Stored vectors were created by a different embedding configuration."""


def default_index_path(repo_path: Path) -> Path:
    normalized_path = os.path.normcase(str(repo_path.resolve()))
    repository_hash = sha256(normalized_path.encode("utf-8")).hexdigest()[:24]
    return (
        Path.home()
        / ".repo_agent"
        / "indexes"
        / repository_hash
        / "index.sqlite3"
    )


class RepositoryIndex:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

        try:
            self._initialize_schema()
        except Exception:
            self._connection.close()
            raise

    def __enter__(self) -> "RepositoryIndex":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def files(self) -> dict[str, ScannedFile]:
        rows = self._connection.execute(
            """
            SELECT relative_path, size_bytes, modified_ns, content_hash
            FROM files
            ORDER BY relative_path
            """
        ).fetchall()
        return {
            row["relative_path"]: ScannedFile(
                relative_path=row["relative_path"],
                size_bytes=row["size_bytes"],
                modified_ns=row["modified_ns"],
                content_hash=row["content_hash"],
            )
            for row in rows
        }

    def compare_files(self, scanned_files: list[ScannedFile]) -> FileChanges:
        scanned_by_path: dict[str, ScannedFile] = {}
        for scanned_file in scanned_files:
            if scanned_file.relative_path in scanned_by_path:
                raise ValueError(
                    f"duplicate scanned path: {scanned_file.relative_path}"
                )
            scanned_by_path[scanned_file.relative_path] = scanned_file

        stored_by_path = self.files()
        added: list[ScannedFile] = []
        modified: list[ScannedFile] = []
        unchanged: list[ScannedFile] = []

        for relative_path in sorted(scanned_by_path):
            scanned_file = scanned_by_path[relative_path]
            stored_file = stored_by_path.get(relative_path)
            if stored_file is None:
                added.append(scanned_file)
            elif stored_file.content_hash != scanned_file.content_hash:
                modified.append(scanned_file)
            else:
                unchanged.append(scanned_file)

        deleted = tuple(sorted(stored_by_path.keys() - scanned_by_path.keys()))
        return FileChanges(
            added=tuple(added),
            modified=tuple(modified),
            unchanged=tuple(unchanged),
            deleted=deleted,
        )

    def update(
        self,
        repo_path: Path,
        scanner: RepositoryScanner,
        chunker: PythonAstChunker,
        embedder: Embedder | None = None,
    ) -> IndexUpdateSummary:
        repo_root = repo_path.resolve()
        scanned_files = scanner.scan(repo_root)
        changes = self.compare_files(scanned_files)
        if embedder is not None:
            self._validate_embedding_profile(embedder)

        prepared_file_chunks: list[tuple[ScannedFile, list[CodeChunk]]] = []
        prepared_backfills: list[tuple[str, bytes]] = []
        skipped_files: list[str] = []

        for scanned_file in (*changes.added, *changes.modified):
            source_path = repo_root / scanned_file.relative_path
            try:
                source = source_path.read_text(encoding="utf-8")
                chunks = chunker.chunk(scanned_file.relative_path, source)
            except (OSError, UnicodeError, PythonChunkingError) as error:
                warnings.warn(
                    f"indexing {scanned_file.relative_path} without chunks: {error}",
                    RepositoryIndexWarning,
                    stacklevel=2,
                )
                chunks = []
                skipped_files.append(scanned_file.relative_path)

            self._validate_chunks(scanned_file, chunks)
            prepared_file_chunks.append((scanned_file, chunks))

        changed_chunks = [
            chunk
            for _, chunks in prepared_file_chunks
            for chunk in chunks
        ]
        changed_embedding_blobs, embedded_chunk_count = self._embed_chunks(
            embedder=embedder,
            chunks=changed_chunks,
            file_path="changed repository chunks",
        )
        changed_blobs_by_id = {
            chunk.chunk_id: blob
            for chunk, blob in zip(
                changed_chunks,
                changed_embedding_blobs,
                strict=True,
            )
        }
        prepared_files = [
            (
                scanned_file,
                chunks,
                [changed_blobs_by_id[chunk.chunk_id] for chunk in chunks],
            )
            for scanned_file, chunks in prepared_file_chunks
        ]
        indexed_chunk_count = len(changed_chunks)

        if embedder is not None:
            excluded_paths = {
                file.relative_path
                for file in (*changes.added, *changes.modified)
            } | set(changes.deleted)
            missing_chunks = self._chunks_without_embeddings(excluded_paths)
            backfill_blobs, embedded_count = self._embed_chunks(
                embedder=embedder,
                chunks=missing_chunks,
                file_path="existing repository chunks",
            )
            embedded_chunk_count += embedded_count
            prepared_backfills.extend(
                (chunk.chunk_id, blob)
                for chunk, blob in zip(
                    missing_chunks,
                    backfill_blobs,
                    strict=True,
                )
                if blob is not None
            )

        with self._connection:
            for relative_path in changes.deleted:
                self._delete_file(relative_path)

            for scanned_file in changes.unchanged:
                self._connection.execute(
                    """
                    UPDATE files
                    SET size_bytes = ?, modified_ns = ?
                    WHERE relative_path = ?
                    """,
                    (
                        scanned_file.size_bytes,
                        scanned_file.modified_ns,
                        scanned_file.relative_path,
                    ),
                )

            for scanned_file, chunks, embedding_blobs in prepared_files:
                self._replace_file(scanned_file, chunks, embedding_blobs)

            for chunk_id, embedding_blob in prepared_backfills:
                self._connection.execute(
                    "UPDATE chunks SET embedding = ? WHERE chunk_id = ?",
                    (embedding_blob, chunk_id),
                )

            if embedder is not None:
                self._set_embedding_profile(embedder)

        return IndexUpdateSummary(
            added_files=len(changes.added),
            modified_files=len(changes.modified),
            unchanged_files=len(changes.unchanged),
            deleted_files=len(changes.deleted),
            indexed_chunks=indexed_chunk_count,
            embedded_chunks=embedded_chunk_count,
            skipped_files=tuple(skipped_files),
        )

    def chunks(self, file_path: str | None = None) -> list[CodeChunk]:
        if file_path is None:
            rows = self._connection.execute(
                """
                SELECT * FROM chunks
                ORDER BY file_path, start_line, end_line, chunk_id
                """
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM chunks
                WHERE file_path = ?
                ORDER BY start_line, end_line, chunk_id
                """,
                (file_path,),
            ).fetchall()
        return [_row_to_chunk(row) for row in rows]

    def get_chunk(self, chunk_id: str) -> CodeChunk | None:
        row = self._connection.execute(
            "SELECT * FROM chunks WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        return _row_to_chunk(row) if row is not None else None

    def search_keyword(self, query: str, limit: int = 20) -> list[CodeChunk]:
        if limit < 1:
            raise ValueError("limit must be positive")

        tokens = _fts_tokens(query)
        expression = _fts_expression(tokens)
        if not expression:
            return []
        exact_term = tokens[0] if len(tokens) == 1 else query.strip()

        rows = self._connection.execute(
            """
            SELECT chunks.*
            FROM chunks_fts
            JOIN chunks ON chunks.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ?
            ORDER BY CASE
                         WHEN lower(chunks.symbol_name) = lower(?) THEN 0
                         WHEN lower(chunks.symbol_name) LIKE '%.' || lower(?) THEN 1
                         ELSE 2
                     END,
                     bm25(chunks_fts, 0.0, 2.0, 5.0, 3.0, 1.0),
                     chunks.file_path,
                     chunks.start_line
            LIMIT ?
            """,
            (expression, exact_term, exact_term, limit),
        ).fetchall()
        return [_row_to_chunk(row) for row in rows]

    def search_vector(
        self,
        query_vector: np.ndarray,
        limit: int = 20,
    ) -> list[CodeChunk]:
        if limit < 1:
            raise ValueError("limit must be positive")

        profile = self.embedding_profile()
        if profile is None:
            return []
        _, dimension = profile
        normalized_query = _normalize_vector(query_vector, dimension)

        rows = self._connection.execute(
            """
            SELECT * FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY file_path, start_line, end_line, chunk_id
            """
        ).fetchall()
        if not rows:
            return []

        vectors = np.vstack(
            [_blob_to_vector(row["embedding"], dimension) for row in rows]
        )
        scores = vectors @ normalized_query
        ranked_indices = np.argsort(-scores, kind="stable")[:limit]
        return [_row_to_chunk(rows[int(index)]) for index in ranked_indices]

    def embedding_profile(self) -> tuple[str, int] | None:
        rows = self._connection.execute(
            """
            SELECT key, value
            FROM metadata
            WHERE key IN ('embedding_model', 'embedding_dimension')
            """
        ).fetchall()
        values = {row["key"]: row["value"] for row in rows}
        if not values:
            return None
        if set(values) != {"embedding_model", "embedding_dimension"}:
            raise IndexVersionError("repository index has incomplete embedding metadata")
        try:
            dimension = int(values["embedding_dimension"])
        except ValueError as error:
            raise IndexVersionError(
                "repository index has an invalid embedding dimension"
            ) from error
        if dimension < 1:
            raise IndexVersionError(
                "repository index has an invalid embedding dimension"
            )
        return values["embedding_model"], dimension

    def _initialize_schema(self) -> None:
        table_names = {
            row["name"]
            for row in self._connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }

        if table_names:
            if "metadata" not in table_names:
                raise IndexVersionError("repository index has no schema metadata")

            row = self._connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None or row["value"] != str(SCHEMA_VERSION):
                actual = row["value"] if row is not None else "missing"
                raise IndexVersionError(
                    f"repository index schema version {actual} is incompatible; "
                    f"expected {SCHEMA_VERSION}"
                )
            return

        self._connection.executescript(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE files (
                relative_path TEXT PRIMARY KEY,
                size_bytes INTEGER NOT NULL,
                modified_ns INTEGER NOT NULL,
                content_hash TEXT NOT NULL
            );

            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                symbol_name TEXT NOT NULL,
                kind TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                code TEXT NOT NULL,
                docstring TEXT,
                parent_symbol TEXT,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                FOREIGN KEY (file_path)
                    REFERENCES files(relative_path)
                    ON DELETE CASCADE
            );

            CREATE INDEX chunks_file_path_idx ON chunks(file_path);
            CREATE INDEX chunks_symbol_name_idx ON chunks(symbol_name);

            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                chunk_id UNINDEXED,
                file_path,
                symbol_name,
                docstring,
                code
            );
            """
        )
        self._connection.execute(
            "INSERT INTO metadata(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._connection.commit()

    def _delete_file(self, relative_path: str) -> None:
        self._connection.execute(
            "DELETE FROM chunks_fts WHERE file_path = ?",
            (relative_path,),
        )
        self._connection.execute(
            "DELETE FROM files WHERE relative_path = ?",
            (relative_path,),
        )

    def _replace_file(
        self,
        scanned_file: ScannedFile,
        chunks: list[CodeChunk],
        embedding_blobs: list[bytes | None],
    ) -> None:
        if len(chunks) != len(embedding_blobs):
            raise ValueError("chunks and embeddings must have the same length")
        self._delete_file(scanned_file.relative_path)
        self._connection.execute(
            """
            INSERT INTO files(
                relative_path,
                size_bytes,
                modified_ns,
                content_hash
            ) VALUES (?, ?, ?, ?)
            """,
            (
                scanned_file.relative_path,
                scanned_file.size_bytes,
                scanned_file.modified_ns,
                scanned_file.content_hash,
            ),
        )

        for chunk, embedding_blob in zip(chunks, embedding_blobs, strict=True):
            self._connection.execute(
                """
                INSERT INTO chunks(
                    chunk_id,
                    file_path,
                    symbol_name,
                    kind,
                    start_line,
                    end_line,
                    code,
                    docstring,
                    parent_symbol,
                    content_hash,
                    embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.file_path,
                    chunk.symbol_name,
                    chunk.kind,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.code,
                    chunk.docstring,
                    chunk.parent_symbol,
                    chunk.content_hash,
                    embedding_blob,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO chunks_fts(
                    chunk_id,
                    file_path,
                    symbol_name,
                    docstring,
                    code
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.file_path,
                    chunk.symbol_name,
                    chunk.docstring or "",
                    chunk.code,
                ),
            )

    @staticmethod
    def _validate_chunks(
        scanned_file: ScannedFile,
        chunks: list[CodeChunk],
    ) -> None:
        chunk_ids: set[str] = set()
        for chunk in chunks:
            if chunk.file_path != scanned_file.relative_path:
                raise ValueError(
                    f"chunk file path does not match scan: {chunk.file_path}"
                )
            if chunk.chunk_id in chunk_ids:
                raise ValueError(f"duplicate chunk_id in file: {chunk.chunk_id}")
            chunk_ids.add(chunk.chunk_id)

    def _validate_embedding_profile(self, embedder: Embedder) -> None:
        profile = self.embedding_profile()
        requested_profile = (embedder.model_name, embedder.dimension)
        if profile is not None and profile != requested_profile:
            raise EmbeddingProfileError(
                "embedding configuration changed; rebuild the repository index"
            )

    def _set_embedding_profile(self, embedder: Embedder) -> None:
        self._connection.executemany(
            """
            INSERT INTO metadata(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (
                ("embedding_model", embedder.model_name),
                ("embedding_dimension", str(embedder.dimension)),
            ),
        )

    def _chunks_without_embeddings(
        self,
        excluded_paths: set[str],
    ) -> list[CodeChunk]:
        rows = self._connection.execute(
            """
            SELECT * FROM chunks
            WHERE embedding IS NULL
            ORDER BY file_path, start_line, end_line, chunk_id
            """
        ).fetchall()
        return [
            _row_to_chunk(row)
            for row in rows
            if row["file_path"] not in excluded_paths
        ]

    @staticmethod
    def _embed_chunks(
        embedder: Embedder | None,
        chunks: list[CodeChunk],
        file_path: str,
        batch_size: int = 256,
    ) -> tuple[list[bytes | None], int]:
        if embedder is None or not chunks:
            return [None] * len(chunks), 0

        blobs: list[bytes | None] = []
        embedded_count = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            try:
                vectors = embedder.embed_passages(
                    [code_chunk_embedding_text(chunk) for chunk in batch]
                )
                array = np.asarray(vectors, dtype=np.float32)
                if array.shape != (len(batch), embedder.dimension):
                    raise EmbeddingError(
                        "embedder returned an unexpected passage matrix shape"
                    )
                batch_blobs = [
                    _normalize_vector(vector, embedder.dimension).tobytes()
                    for vector in array
                ]
                blobs.extend(batch_blobs)
                embedded_count += len(batch_blobs)
            except (EmbeddingError, ValueError) as error:
                warnings.warn(
                    f"indexing {file_path} without embeddings: {error}",
                    RepositoryIndexWarning,
                    stacklevel=2,
                )
                blobs.extend([None] * len(batch))
        return blobs, embedded_count


def _row_to_chunk(row: sqlite3.Row) -> CodeChunk:
    return CodeChunk(
        chunk_id=row["chunk_id"],
        file_path=row["file_path"],
        symbol_name=row["symbol_name"],
        kind=row["kind"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        code=row["code"],
        docstring=row["docstring"],
        parent_symbol=row["parent_symbol"],
        content_hash=row["content_hash"],
    )


def _fts_tokens(query: str) -> list[str]:
    return re.findall(r"\w+(?:[._]\w+)*", query, flags=re.UNICODE)


def _fts_expression(tokens: list[str]) -> str:
    return " OR ".join(f'"{token}"' for token in tokens)


def _normalize_vector(vector: np.ndarray, dimension: int) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    if array.shape != (dimension,):
        raise ValueError(
            f"embedding vector must have shape ({dimension},), got {array.shape}"
        )
    if not np.isfinite(array).all():
        raise ValueError("embedding vector must contain only finite values")
    norm = float(np.linalg.norm(array))
    if norm == 0:
        raise ValueError("embedding vector must not be zero")
    return np.ascontiguousarray(array / norm, dtype=np.float32)


def _blob_to_vector(blob: bytes, dimension: int) -> np.ndarray:
    vector = np.frombuffer(blob, dtype=np.float32)
    if vector.shape != (dimension,):
        raise IndexVersionError(
            "repository index contains an invalid embedding vector"
        )
    return vector
