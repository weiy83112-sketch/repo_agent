from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError

from repo_agent.exceptions import ModelServiceError
from repo_agent.model_router import ModelRouter


class FakeCompletions:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return "fake response"


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_complex_uses_pro_high_with_thinking() -> None:
    client = FakeClient()
    router = ModelRouter(client=client)

    response = router.complex(messages=[{"role": "user", "content": "question"}], tools=[])

    assert response == "fake response"
    assert client.completions.requests == [
        {
            "model": "deepseek-v4-pro",
            "messages": [{"role": "user", "content": "question"}],
            "tools": [],
            "stream": False,
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
    ]


def test_simple_uses_flash_high_with_thinking() -> None:
    client = FakeClient()
    router = ModelRouter(client=client)

    router.simple(messages=[{"role": "user", "content": "question"}], tools=[])

    assert client.completions.requests[0]["model"] == "deepseek-v4-flash"
    assert client.completions.requests[0]["reasoning_effort"] == "high"
    assert client.completions.requests[0]["extra_body"] == {
        "thinking": {"type": "enabled"}
    }


def test_model_metadata_matches_selected_capability() -> None:
    router = ModelRouter(client=FakeClient())

    metadata = router.model_metadata("simple")

    assert metadata.capability == "simple"
    assert metadata.model == "deepseek-v4-flash"
    assert metadata.thinking == "enabled"
    assert metadata.reasoning_effort == "high"


def test_router_translates_non_timeout_sdk_error() -> None:
    client = FakeClient()

    def raise_connection_error(**kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "https://api.deepseek.com"))

    client.completions.create = raise_connection_error
    router = ModelRouter(client=client)

    with pytest.raises(ModelServiceError, match="Model service request failed"):
        router.simple(messages=[], tools=[])
