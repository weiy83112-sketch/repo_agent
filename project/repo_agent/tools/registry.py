from pathlib import Path  # 导入 Path，用来标注受程序控制的仓库路径

from .file_tools import list_files, read_file, search_text  # 导入三个真实的 Python 工具函数


# 创建工具注册表：左边是工具名称，右边是真实函数
TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
    "search_text": search_text,
}


# 创建给大模型阅读的工具说明列表
TOOL_SCHEMAS = [
    {
        "type": "function",  # 说明这是一个函数工具
        "function": {
            "name": "list_files",  # 必须与注册表中的工具名称一致
            "description": "List files and folders in the repository root.",
            "parameters": {
                "type": "object",  # 模型输出的 arguments 必须是对象
                "properties": {},  # repo_path 由程序注入，模型不需要提供参数
                "required": [],  # 没有必须由模型提供的参数
                "additionalProperties": False,  # 禁止模型添加未定义参数
            },
        },
    },
    {
        "type": "function",  # 说明这是一个函数工具
        "function": {
            "name": "read_file",  # 必须与注册表中的工具名称一致
            "description": "Read a UTF-8 text file inside the repository.",
            "parameters": {
                "type": "object",  # 模型输出的 arguments 必须是对象
                "properties": {
                    "relative_path": {
                        "type": "string",  # relative_path 必须是字符串
                        "description": "Repository-relative file path, for example README.md.",
                    }
                },
                "required": ["relative_path"],  # 模型必须提供 relative_path
                "additionalProperties": False,  # 禁止模型添加未定义参数
            },
        },
    },
    {
        "type": "function",  # 说明这是一个函数工具
        "function": {
            "name": "search_text",  # 必须与注册表中的工具名称一致
            "description": "Search Python files in the repository for matching text.",
            "parameters": {
                "type": "object",  # 模型输出的 arguments 必须是对象
                "properties": {
                    "query": {
                        "type": "string",  # query 必须是字符串
                        "description": "Text to search for in Python files.",
                    }
                },
                "required": ["query"],  # 模型必须提供 query
                "additionalProperties": False,  # 禁止模型添加未定义参数
            },
        },
    },
]


def get_tool(name: str):  # 根据工具名称查找并返回真实函数
    if name not in TOOL_REGISTRY:  # 判断模型给出的工具名称是否存在
        raise ValueError(f"unknown tool: {name}")  # 不存在就主动抛出错误

    return TOOL_REGISTRY[name]  # 通过工具名称取得并返回真实函数


def execute_tool(repo_path: Path, name: str, arguments: dict):  # 执行模型选择的工具
    tool = get_tool(name)  # 通过工具名称取得真实的 Python 函数

    # ** 会把字典拆成“参数名=参数值”，再与程序控制的 repo_path 一起传给函数
    return tool(repo_path=repo_path, **arguments)
