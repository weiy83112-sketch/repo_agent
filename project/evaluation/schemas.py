from typing import Literal, TypedDict


# 限制评测题类别只能从这四个字符串中选择，避免同一类别出现多种拼写
EvaluationCategory = Literal[
    "entry_point",
    "feature_location",
    "call_chain",
    "related_files",
]


# 描述一条评测题字典必须拥有的键，以及每个值的数据类型 就是schemas
class EvaluationCase(TypedDict):
    # 稳定标识同一道题，使不同 Agent 结果可以对应且不依赖 JSONL 行号
    case_id: str
    # 指定这道题应该在哪一个固定仓库快照中运行
    repository: str
    # 旧 Agent 和新 Agent 都要回答的固定问题
    question: str
    # 人工检查真实代码后确认的正确文件路径，可以包含多个文件
    expected_files: list[str]
    # 人工确认的正确类名或函数名，可以包含多个符号
    expected_symbols: list[str]
    # 标记题目属于入口、功能位置、调用链或相关文件中的哪一类
    category: EvaluationCategory
