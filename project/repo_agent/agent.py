import json
from pathlib import Path

from .model_router import ModelRouter
from .state import add_message, create_initial_state
from .tools.registry import TOOL_SCHEMAS, execute_tool


def run_agent(
    repo_path: Path,
    question: str,
    router: ModelRouter,
    max_steps: int = 10,
) -> str:
    state = create_initial_state(question)
    steps = 0

    while True:
        if steps >= max_steps:
            raise RuntimeError("Agent exceeded the maximum number of steps")

        steps += 1
        response = router.complex(
            messages=state["messages"],
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message

        if message.tool_calls:#模型请求工具
            state["messages"].append(message.model_dump(exclude_none=True))

            for tool_call in message.tool_calls:
                try:
                    #解析模型json参数
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_tool(#匹配工具
                        repo_path=repo_path,
                        name=tool_call.function.name,
                        arguments=arguments,
                    )

                    if isinstance(result, str):
                        tool_content = result
                    else:
                        tool_content = json.dumps(result, ensure_ascii=False)
                except (ValueError, OSError, UnicodeError) as error:
                    tool_content = f"tool error: {error}"

                state["messages"].append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_content,
                    }
                )

            continue

        if message.content is None:
            raise ValueError("model response has no content or tool calls")

        add_message(
            state=state,
            role="assistant",
            content=message.content,
        )
        return message.content
