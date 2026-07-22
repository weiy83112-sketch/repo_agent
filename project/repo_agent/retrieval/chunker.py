import ast
from dataclasses import dataclass
from hashlib import sha256

from .models import ChunkKind, CodeChunk


class PythonChunkingError(ValueError):
    """A Python source file cannot be converted into code chunks."""


@dataclass(frozen=True, slots=True)
class _PendingChunk:
    symbol_name: str
    kind: ChunkKind
    start_line: int
    end_line: int
    code: str
    docstring: str | None
    parent_symbol: str | None


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]) -> None:
        self._source_lines = source_lines
        self._symbol_stack: list[tuple[str, ChunkKind]] = []
        self.chunks: list[_PendingChunk] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        symbol_name = self._qualified_name(node.name)
        self.chunks.append(
            self._create_pending_chunk(
                node=node,
                symbol_name=symbol_name,
                kind="class",
            )
        )

        self._symbol_stack.append((symbol_name, "class"))
        self.generic_visit(node)
        self._symbol_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        symbol_name = self._qualified_name(node.name)
        kind: ChunkKind = (
            "method"
            if self._symbol_stack and self._symbol_stack[-1][1] == "class"
            else "function"
        )
        self.chunks.append(
            self._create_pending_chunk(
                node=node,
                symbol_name=symbol_name,
                kind=kind,
            )
        )

        self._symbol_stack.append((symbol_name, kind))
        self.generic_visit(node)
        self._symbol_stack.pop()

    def _qualified_name(self, name: str) -> str:
        if not self._symbol_stack:
            return name
        return f"{self._symbol_stack[-1][0]}.{name}"

    def _create_pending_chunk(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        symbol_name: str,
        kind: ChunkKind,
    ) -> _PendingChunk:
        start_line = _node_start_line(node)
        end_line = _node_end_line(node)
        return _PendingChunk(
            symbol_name=symbol_name,
            kind=kind,
            start_line=start_line,
            end_line=end_line,
            code=_source_slice(self._source_lines, start_line, end_line),
            docstring=ast.get_docstring(node, clean=False),
            parent_symbol=(
                self._symbol_stack[-1][0]
                if self._symbol_stack
                else None
            ),
        )


class PythonAstChunker:
    def chunk(self, relative_path: str, source: str) -> list[CodeChunk]:
        if not relative_path:
            raise ValueError("relative_path must not be empty")

        try:
            tree = ast.parse(
                source,
                filename=relative_path,
                type_comments=True,
            )
        except SyntaxError as error:
            location = f":{error.lineno}" if error.lineno is not None else ""
            raise PythonChunkingError(
                f"{relative_path}{location}: invalid Python syntax"
            ) from error

        source_lines = source.splitlines()
        pending_chunks = self._module_chunks(tree, source_lines)

        visitor = _SymbolVisitor(source_lines)
        visitor.visit(tree)
        pending_chunks.extend(visitor.chunks)
        pending_chunks.sort(
            key=lambda item: (
                item.start_line,
                item.end_line,
                item.kind,
                item.symbol_name,
            )
        )

        identity_counts: dict[tuple[ChunkKind, str], int] = {}
        chunks: list[CodeChunk] = []

        for pending in pending_chunks:
            identity = (pending.kind, pending.symbol_name)
            occurrence = identity_counts.get(identity, 0)
            identity_counts[identity] = occurrence + 1

            chunks.append(
                CodeChunk(
                    chunk_id=_chunk_id(
                        relative_path=relative_path,
                        kind=pending.kind,
                        symbol_name=pending.symbol_name,
                        occurrence=occurrence,
                    ),
                    file_path=relative_path,
                    symbol_name=pending.symbol_name,
                    kind=pending.kind,
                    start_line=pending.start_line,
                    end_line=pending.end_line,
                    code=pending.code,
                    docstring=pending.docstring,
                    parent_symbol=pending.parent_symbol,
                    content_hash=sha256(pending.code.encode("utf-8")).hexdigest(),
                )
            )

        return chunks

    @staticmethod
    def _module_chunks(
        tree: ast.Module,
        source_lines: list[str],
    ) -> list[_PendingChunk]:
        groups: list[list[ast.stmt]] = []
        current_group: list[ast.stmt] = []

        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if current_group:
                    groups.append(current_group)
                    current_group = []
                continue

            current_group.append(node)

        if current_group:
            groups.append(current_group)

        module_docstring = ast.get_docstring(tree, clean=False)
        module_chunks: list[_PendingChunk] = []

        for group_index, group in enumerate(groups):
            start_line = min(node.lineno for node in group)
            end_line = max(_node_end_line(node) for node in group)
            module_chunks.append(
                _PendingChunk(
                    symbol_name="<module>",
                    kind="module",
                    start_line=start_line,
                    end_line=end_line,
                    code=_source_slice(source_lines, start_line, end_line),
                    docstring=module_docstring if group_index == 0 else None,
                    parent_symbol=None,
                )
            )

        return module_chunks


def _node_start_line(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    decorator_lines = [decorator.lineno for decorator in node.decorator_list]
    return min([node.lineno, *decorator_lines])


def _node_end_line(node: ast.AST) -> int:
    if node.end_lineno is None:
        raise PythonChunkingError("AST node has no end line")
    return node.end_lineno


def _source_slice(source_lines: list[str], start_line: int, end_line: int) -> str:
    return "\n".join(source_lines[start_line - 1 : end_line])


def _chunk_id(
    relative_path: str,
    kind: ChunkKind,
    symbol_name: str,
    occurrence: int,
) -> str:
    identity = f"{relative_path}\0{kind}\0{symbol_name}\0{occurrence}"
    return sha256(identity.encode("utf-8")).hexdigest()
