import os  # 导入 os，用于读取环境变量
from pathlib import Path  # 导入 Path，用于定位项目中的 .env 文件

from dotenv import load_dotenv  # 导入 .env 文件加载工具
from openai import APITimeoutError, OpenAI  # 导入客户端及其模型请求超时异常

from repo_agent.exceptions import AgentTimeoutError  # 导入项目级超时异常，隔离 SDK 细节


# __file__ 是当前 model_router.py 文件路径
# parent 是 repo_agent 文件夹，parent.parent 是 project 文件夹
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 从 project/.env 读取变量，并写入当前 Python 进程的环境变量
load_dotenv(PROJECT_DIR / ".env")


class ModelRouter:
    # 创建路由对象时，读取 Key 并创建 DeepSeek 客户端
    def __init__(self):
        # 从环境变量读取 Key，不把 Key 写进 Python 源码
        api_key = os.environ.get("DEEPSEEK_API_KEY")

        # Key 缺失时主动停止，避免后面出现难懂的 API 报错
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")

        # 保存客户端；base_url 把 OpenAI SDK 指向 DeepSeek API
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=60.0,  # 单次模型请求最多等待 60 秒，避免 call_model 长时间卡住
        )

    # Agent 通过 complex 能力进行一次复杂模型调用
    def complex(self, messages, tools):
        try:
            # 模型名称只保留在路由层，未来 Agent 不需要知道它
            # tools 把注册表中的工具说明交给模型，但真实工具仍由 Agent 执行
            return self._client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=messages,
                tools=tools,
                stream=False,
            )
        except APITimeoutError as error:
            # 将 SDK 异常转换成项目异常，外层不需要依赖 OpenAI SDK
            raise AgentTimeoutError("Model request timed out") from error
