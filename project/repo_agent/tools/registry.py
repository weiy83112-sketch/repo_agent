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


# [Agent 补充的小细节] 根据工具名称取得参数 schema，供运行时校验使用
def get_tool_parameters(name: str) -> dict:
    for tool_schema in TOOL_SCHEMAS:  # 逐个检查给模型阅读的工具说明
        function_schema = tool_schema["function"]  # 取得当前工具的函数说明

        if function_schema["name"] == name:  # 找到名称相同的工具说明
            return function_schema["parameters"]  # 返回它的参数规则

    raise ValueError(f"tool schema not found: {name}")  # 注册表和 schema 不同步时主动报错


# [Agent 补充的小细节] 按 TOOL_SCHEMAS 检查模型提供的参数
def validate_tool_arguments(name: str, arguments: dict) -> None:
    if not isinstance(arguments, dict):  # JSON object 解析到 Python 后必须是字典
        raise ValueError("tool arguments must be an object")

    parameters = get_tool_parameters(name)  # 取得当前工具的参数规则 会从TOOL_SCHEMAS中找到read_file规则
    properties = parameters["properties"]  # 取得允许出现的参数及其类型
    required = parameters["required"]  # 取得必须提供的参数名称
    #所有不在agent给到的参数 缺失部分
    missing = [key for key in required if key not in arguments]  # 找出缺少的必填参数
    if missing:
        raise ValueError(f"missing required tool arguments: {', '.join(missing)}")#用逗号链接起来

    unexpected = [key for key in arguments if key not in properties]  # 找出 schema 未声明的参数
    if unexpected:#这一步抛出传入的多余参数
        raise ValueError(f"unexpected tool arguments: {', '.join(unexpected)}")

    for key, value in arguments.items():  # 逐个检查已有参数的值类型 字典的item取出键值对
        expected_type = properties[key]["type"]  # 读取 schema 声明的 JSON 类型

        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"tool argument '{key}' must be a string")


def execute_tool(repo_path: Path, name: str, arguments: dict):  # 执行模型选择的工具
    tool = get_tool(name)  # 通过工具名称取得真实的 Python 函数
    validate_tool_arguments(name, arguments)  # 执行前先校验模型提供的参数

    # ** 会把字典拆成“参数名=参数值”，再与程序控制的 repo_path 一起传给函数
    return tool(repo_path=repo_path, **arguments)
