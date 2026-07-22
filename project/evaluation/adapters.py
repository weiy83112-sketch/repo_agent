from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol

from repo_agent.langgraph_agent import run_graph_agent
from repo_agent.model_router import ModelCapability, ModelMetadata, ModelRouter
from repo_agent.retrieval import (
    ContextBuilder,
    Embedder,
    HybridRetriever,
    PythonAstChunker,
    RepositoryIndex,
    RepositoryScanner,
    SentenceTransformerEmbedder,
    default_index_path,
)


class EvaluationAgent(Protocol):
    """Runner 所依赖的最小 Agent 接口。"""

    @property
    def model_metadata(self) -> ModelMetadata: ...

    def run(
        self,
        repo_path: Path,
        question: str,
        on_tool_call: Callable[[str, dict], None] | None,
    ) -> str: ...


class BaselineAgentAdapter:
    """把现有 LangGraph 文件工具 Agent 适配成统一评测接口。"""

    def __init__(
        self,
        router: ModelRouter,
        capability: ModelCapability,
        max_graph_steps: int = 20,
    ) -> None:
        self._router = router
        self._capability = capability
        self._max_graph_steps = max_graph_steps

    @property
    def model_metadata(self) -> ModelMetadata:
        return self._router.model_metadata(self._capability)

    def run(
        self,
        repo_path: Path,
        question: str,
        on_tool_call: Callable[[str, dict], None] | None,
    ) -> str:
        return run_graph_agent(
            repo_path=repo_path,
            question=question,
            router=self._router,
            capability=self._capability,
            max_graph_steps=self._max_graph_steps,
            on_tool_call=on_tool_call,
        )


@dataclass(frozen=True, slots=True)
class _RepositoryRetrievalRuntime:
    index: RepositoryIndex
    retriever: HybridRetriever


class HybridRagAgentAdapter:
    """为统一评测接口准备并复用每个仓库的 Hybrid RAG 运行时。"""

    def __init__(
        self,
        router: ModelRouter,
        capability: ModelCapability,
        max_graph_steps: int = 20,
        embedder: Embedder | None = None,
        context_builder: ContextBuilder | None = None,
        index_path_factory: Callable[[Path], Path] = default_index_path,
    ) -> None:
        self._router = router
        self._capability = capability
        self._max_graph_steps = max_graph_steps
        self._embedder = embedder
        self._context_builder = context_builder or ContextBuilder()
        self._index_path_factory = index_path_factory
        self._runtimes: dict[Path, _RepositoryRetrievalRuntime] = {}
        self._closed = False

    @property
    def model_metadata(self) -> ModelMetadata:
        return self._router.model_metadata(self._capability)

    def run(
        self,
        repo_path: Path,
        question: str,
        on_tool_call: Callable[[str, dict], None] | None,
    ) -> str:
        runtime = self._runtime_for(repo_path)
        return run_graph_agent(
            repo_path=repo_path,
            question=question,
            router=self._router,
            capability=self._capability,
            max_graph_steps=self._max_graph_steps,
            on_tool_call=on_tool_call,
            retriever=runtime.retriever,
            context_builder=self._context_builder,
        )

    def close(self) -> None:
        if self._closed:
            return

        for runtime in self._runtimes.values():
            runtime.index.close()
        self._runtimes.clear()
        self._closed = True

    def __enter__(self) -> "HybridRagAgentAdapter":
        if self._closed:
            raise RuntimeError("HybridRagAgentAdapter is closed")
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _runtime_for(self, repo_path: Path) -> _RepositoryRetrievalRuntime:
        if self._closed:
            raise RuntimeError("HybridRagAgentAdapter is closed")

        repo_root = repo_path.resolve()
        runtime = self._runtimes.get(repo_root)
        if runtime is not None:
            return runtime

        embedder = self._get_embedder()
        index = RepositoryIndex(self._index_path_factory(repo_root))
        try:
            index.update(
                repo_path=repo_root,
                scanner=RepositoryScanner(),
                chunker=PythonAstChunker(),
                embedder=embedder,
            )
        except BaseException:
            index.close()
            raise

        runtime = _RepositoryRetrievalRuntime(
            index=index,
            retriever=HybridRetriever(index=index, embedder=embedder),
        )
        self._runtimes[repo_root] = runtime
        return runtime

    def _get_embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = SentenceTransformerEmbedder(local_files_only=True)
        return self._embedder
