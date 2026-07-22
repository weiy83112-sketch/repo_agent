from dataclasses import dataclass
from pathlib import Path

from repo_agent.retrieval import ContextBuilder, HybridRetriever


@dataclass(frozen=True, slots=True)
class ToolRuntime:
    """Dependencies controlled by the application rather than by the model."""

    repo_path: Path
    retriever: HybridRetriever | None = None
    context_builder: ContextBuilder | None = None

