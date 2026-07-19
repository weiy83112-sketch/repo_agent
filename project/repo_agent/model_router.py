import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import APIError, APITimeoutError, OpenAI

from repo_agent.exceptions import AgentTimeoutError, ModelServiceError


# __file__ 是当前 model_router.py；parent.parent 是 project 文件夹。
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 把 project/.env 中的变量加载进当前 Python 进程的 os.environ。
load_dotenv(PROJECT_DIR / ".env")


ModelCapability = Literal["complex", "simple"]


@dataclass(frozen=True)
class ModelMetadata:
    """一次模型能力对应的只读配置，也是评测结果要保存的模型元数据。"""

    capability: ModelCapability
    model: str
    thinking: str
    reasoning_effort: str


_MODEL_PROFILES: dict[ModelCapability, ModelMetadata] = {
    "complex": ModelMetadata(
        capability="complex",
        model="deepseek-v4-pro",
        thinking="enabled",
        reasoning_effort="high",
    ),
    "simple": ModelMetadata(
        capability="simple",
        model="deepseek-v4-flash",
        thinking="enabled",
        reasoning_effort="high",
    ),
}


class ModelRouter:
    def __init__(self, client: Any | None = None):
        # 正式运行不传 client：从环境变量读取 Key 并创建 DeepSeek 客户端。
        # 测试可以传入 FakeClient，因此不会发出真实请求，也不需要读取 Key。
        if client is not None:
            self._client = client
            return

        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=60.0,
        )

    def model_metadata(self, capability: ModelCapability) -> ModelMetadata:
        """返回能力对应的只读元数据，Runner 不需要重复模型名称。"""

        return _MODEL_PROFILES[capability]

    def _complete(self, capability: ModelCapability, messages, tools):
        """根据能力配置发送一次共享的 Chat Completions 请求。"""

        metadata = self.model_metadata(capability)

        try:
            return self._client.chat.completions.create(
                model=metadata.model,
                messages=messages,
                tools=tools,
                stream=False,
                reasoning_effort=metadata.reasoning_effort,
                # OpenAI SDK 没有独立的 thinking 参数；extra_body 会把
                # DeepSeek 扩展字段原样加入最终 HTTP 请求体。
                extra_body={"thinking": {"type": metadata.thinking}},
            )
        except APITimeoutError as error:
            # 把 SDK 异常转换为项目异常，外层不必依赖 OpenAI SDK 类型。
            raise AgentTimeoutError("Model request timed out") from error
        except APIError as error:
            # 连接失败、无效 Key、余额不足和模型配置错误都会停止整轮评测。
            # Runner 不捕获这个项目级异常，因此不会把环境问题伪装成单题失败。
            raise ModelServiceError("Model service request failed") from error

    def complex(self, messages, tools):
        """使用复杂能力（DeepSeek Pro High）调用一次模型。"""

        return self._complete("complex", messages, tools)

    def simple(self, messages, tools):
        """使用简单能力（DeepSeek Flash High）调用一次模型。"""

        return self._complete("simple", messages, tools)
