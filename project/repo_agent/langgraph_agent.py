import json
from collections.abc import Callable
from pathlib import Path

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from repo_agent.exceptions import AgentLimitError, AgentResponseError
from repo_agent.model_router import ModelCapability, ModelRouter
from repo_agent.state import AgentState, create_initial_state
from repo_agent.tools.registry import TOOL_SCHEMAS, execute_tool


# 接收现有 ModelRouter，并开始构建 LangGraph Agent
def build_graph(
    repo_path: Path,
    router: ModelRouter,
    capability: ModelCapability = "complex",
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> CompiledStateGraph:
    # 创建一个 LangGraph 构建器，并让整张图使用 AgentState 管理共享状态
    graph_builder = StateGraph(AgentState)

    # 创建图时选定本轮使用的能力；call_model 闭包会一直记住这个函数。
    model_call = {
        "complex": router.complex,
        "simple": router.simple,
    }[capability]

    # call_model 是第一个节点：接收当前完整 State，调用一次模型
    def call_model(state: AgentState) -> dict:
        response = model_call(
            messages=state["messages"],
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message

        # 节点只返回本次更新；messages 的 add reducer 会负责追加到旧列表
        return {
            "messages": [message.model_dump(exclude_none=True)],
        }

    # 根据最新模型消息决定下一步：执行工具，或者结束本次 Agent 运行
    def route_after_model(state: AgentState) -> str:
        latest_message = state["messages"][-1]

        if latest_message.get("tool_calls"):
            return "tools"

        return "end"

    # 执行最新 assistant 消息中的所有工具调用，并生成对应的 tool 消息
    def execute_tools(state: AgentState) -> dict:
        latest_message = state["messages"][-1]
        tool_messages = []

        for tool_call in latest_message["tool_calls"]:
            try:
                function = tool_call["function"]
                arguments = json.loads(function["arguments"])

                # 如果调用者提供了回调，就在真实工具执行前报告工具名称和参数
                if on_tool_call is not None:
                    on_tool_call(
                        function["name"],
                        arguments,
                    )

                result = execute_tool(
                    repo_path=repo_path,
                    name=function["name"],
                    arguments=arguments,
                )

                if isinstance(result, str):
                    tool_content = result
                else:
                    tool_content = json.dumps(result, ensure_ascii=False)
            except (ValueError, OSError, UnicodeError) as error:
                tool_content = f"tool error: {error}"

            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_content,
                }
            )

        # 节点只返回本次新增的工具消息，由 messages reducer 追加到 State
        return {
            "messages": tool_messages,
        }

    # 将普通 Python 函数登记为图中的 call_model 节点
    graph_builder.add_node("call_model", call_model)

    # 将工具执行函数登记为条件分支可以到达的 execute_tools 节点
    graph_builder.add_node("execute_tools", execute_tools)

    # 指定图的入口：运行开始后，第一个执行 call_model 节点
    graph_builder.add_edge(START, "call_model")

    # call_model 之后不固定走一条边，而是根据 route_after_model 的结果选择分支
    graph_builder.add_conditional_edges(
        "call_model",
        route_after_model,
        {
            "tools": "execute_tools",  # 路由返回 tools 时，执行工具节点
            "end": END,  # 路由返回 end 时，结束整张图
        },
    )

    # 工具结果写入 State 后，固定回到模型节点继续判断
    graph_builder.add_edge("execute_tools", "call_model")

    # 将搭建完成的 StateGraph 编译为可以 invoke 的运行图
    graph = graph_builder.compile()

    return graph


# 接收一次用户问题，运行整张 LangGraph，并返回最终回答文本
def run_graph_agent(
    repo_path: Path,
    question: str,
    router: ModelRouter,
    capability: ModelCapability = "complex",
    max_graph_steps: int = 20,
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> str:
    # 根据当前仓库路径和模型路由创建可 invoke 的运行图
    graph = build_graph(
        repo_path=repo_path,
        router=router,
        capability=capability,
        on_tool_call=on_tool_call,
    )

    # 将用户问题转换成 LangGraph 需要的初始 State
    initial_state = create_initial_state(question)

    try:
        # 每次问题最多执行指定数量的图节点步骤，防止模型和工具无限循环
        final_state = graph.invoke(
            initial_state,
            config={"recursion_limit": max_graph_steps},
        )
    except GraphRecursionError as error:
        # 隔离 LangGraph 细节：向外只暴露项目自己的 Agent 限制异常
        raise AgentLimitError(
            "Agent exceeded the maximum number of graph steps"
        ) from error

    # 图正常结束时，最后一条消息应当是 assistant 的最终回答
    final_message = final_state["messages"][-1]
    content = final_message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise AgentResponseError("final assistant message has no text content")

    return content
