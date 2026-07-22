from pathlib import Path
from types import SimpleNamespace

import pytest

import repo_agent.langgraph_agent as langgraph_agent
from repo_agent.exceptions import AgentResponseError


class FakeGraph:
    def invoke(self, initial_state, config):
        return {"messages": [{"role": "assistant", "content": "   "}]}


class FakeMessage:
    def __init__(self, content=None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True) -> dict:
        result = {"role": "assistant"}
        if self.content is not None or not exclude_none:
            result["content"] = self.content
        if self.tool_calls is not None or not exclude_none:
            result["tool_calls"] = self.tool_calls
        return result


class FakeRouter:
    def __init__(self, messages: list[FakeMessage]) -> None:
        self._messages = iter(messages)
        self.calls: list[dict] = []

    def complex(self, *, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=next(self._messages))]
        )

    simple = complex


class FakeRetriever:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def retrieve(self, question: str) -> list:
        self.questions.append(question)
        return ["retrieved chunk"]


class FakeContextBuilder:
    def __init__(self) -> None:
        self.inputs: list[list] = []

    def build(self, chunks: list) -> str:
        self.inputs.append(chunks)
        return "evidence from repo_agent/model_router.py:10"


def test_graph_agent_rejects_blank_final_answer(monkeypatch) -> None:
    monkeypatch.setattr(langgraph_agent, "build_graph", lambda **kwargs: FakeGraph())

    with pytest.raises(AgentResponseError, match="no text content"):
        langgraph_agent.run_graph_agent(
            repo_path=Path("repository"),
            question="question",
            router=SimpleNamespace(),
        )


def test_rag_graph_retrieves_once_and_adds_temporary_context(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("repository", encoding="utf-8")
    router = FakeRouter(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"relative_path": "README.md"}',
                        },
                    }
                ]
            ),
            FakeMessage(content="final answer"),
        ]
    )
    retriever = FakeRetriever()
    context_builder = FakeContextBuilder()

    answer = langgraph_agent.run_graph_agent(
        repo_path=tmp_path,
        question="Where is the model client?",
        router=router,
        retriever=retriever,
        context_builder=context_builder,
    )

    assert answer == "final answer"
    assert retriever.questions == ["Where is the model client?"]
    assert context_builder.inputs == [["retrieved chunk"]]
    assert len(router.calls) == 2
    assert [message["role"] for message in router.calls[0]["messages"]] == [
        "system",
        "user",
    ]
    assert [message["role"] for message in router.calls[1]["messages"]] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    assert sum(
        message["role"] == "system"
        for message in router.calls[1]["messages"]
    ) == 1
    assert router.calls[0]["messages"][0]["content"].endswith(
        "evidence from repo_agent/model_router.py:10"
    )
    assert [tool["function"]["name"] for tool in router.calls[0]["tools"]] == [
        "list_files",
        "read_file",
        "search_text",
        "search_code",
    ]


def test_baseline_graph_keeps_original_messages_and_tools(tmp_path: Path) -> None:
    router = FakeRouter([FakeMessage(content="baseline answer")])

    answer = langgraph_agent.run_graph_agent(
        repo_path=tmp_path,
        question="question",
        router=router,
    )

    assert answer == "baseline answer"
    assert router.calls[0]["messages"] == [
        {"role": "user", "content": "question"}
    ]
    assert [tool["function"]["name"] for tool in router.calls[0]["tools"]] == [
        "list_files",
        "read_file",
        "search_text",
    ]


def test_rag_dependencies_must_be_provided_together(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        langgraph_agent.build_graph(
            repo_path=tmp_path,
            router=FakeRouter([]),
            retriever=FakeRetriever(),
        )
