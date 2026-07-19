from pathlib import Path
from types import SimpleNamespace

import pytest

import repo_agent.langgraph_agent as langgraph_agent
from repo_agent.exceptions import AgentResponseError


class FakeGraph:
    def invoke(self, initial_state, config):
        return {"messages": [{"role": "assistant", "content": "   "}]}


def test_graph_agent_rejects_blank_final_answer(monkeypatch) -> None:
    monkeypatch.setattr(langgraph_agent, "build_graph", lambda **kwargs: FakeGraph())

    with pytest.raises(AgentResponseError, match="no text content"):
        langgraph_agent.run_graph_agent(
            repo_path=Path("repository"),
            question="question",
            router=SimpleNamespace(),
        )
