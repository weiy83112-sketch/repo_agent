# 创建一次 Agent 任务刚开始时的状态
def create_initial_state(question: str) -> dict:
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
def add_message(state: dict, role: str, content: str) -> None:
    # 取得 State 中已有的 messages 列表，并在末尾加入一条新记录
    state["messages"].append(
        {
            "role": role,
            "content": content,
        }
    )
