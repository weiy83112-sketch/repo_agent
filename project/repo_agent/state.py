from operator import add
from typing import Annotated, TypedDict


# 描述 LangGraph 中共享 State 的结构，以及每个字段的更新规则
class AgentState(TypedDict): #typedict类似schema
    # messages 的数据类型是列表，列表中的每一项是字典
    # add 是 reducer：节点返回新消息列表时，将其追加到旧列表后面 描述字段的更新方式
    messages: Annotated[list[dict], add]


# 创建一次 Agent 任务刚开始时的状态
def create_initial_state(question: str) -> AgentState:
    # 将用户问题保存为第一条 message
    return {
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ]
    }


# 将模型动作、工具结果或最终回答追加到已有 State
def add_message(state: AgentState, role: str, content: str) -> None:
    # 取得 State 中已有的 messages 列表，并在末尾加入一条新记录
    state["messages"].append(
        {
            "role": role,
            "content": content,
        }
    )
