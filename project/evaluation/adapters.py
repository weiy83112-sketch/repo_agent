from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from repo_agent.langgraph_agent import run_graph_agent
from repo_agent.model_router import ModelCapability, ModelMetadata, ModelRouter


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
