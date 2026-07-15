import argparse  # 导入 Python 内置的命令行参数解析工具
from pathlib import Path  # 导入 Path，用对象表示文件夹路径

from .agent import run_agent  # 导入 Agent loop，将自然语言问题交给 Agent 处理
from .model_router import ModelRouter  # 导入模型路由，供整个 CLI 会话重复使用
from .tools.file_tools import list_files, read_file, search_text  # 导入三个只读工具


def parse_args() -> Path:  # 定义参数解析函数，返回仓库的 Path 对象
    parser = argparse.ArgumentParser(  # 创建命令行参数解析器
        description="A CLI Agent that reads a local repository."
    )

    parser.add_argument(  # 注册程序支持的 --repo 参数
        "--repo",  # 参数名称
        type=Path,  # 把用户输入的字符串转换成 Path
        required=True,  # 要求用户必须提供这个参数
        help="Path to the repository the Agent may read.",
    )

    args = parser.parse_args()  # 解析终端传入的全部参数
    repo_path = args.repo.resolve()  # 取得 repo 参数并转换成绝对路径

    if not repo_path.is_dir():  # 检查仓库路径是否为真实文件夹
        parser.error(f"repository not found: {repo_path}")  # 报错并退出

    return repo_path  # 返回检查通过的仓库路径


def main() -> None:  # 定义 CLI 程序的主函数
    repo_path = parse_args()  # 解析参数并得到目标仓库路径
    router = ModelRouter()  # 创建一次模型路由；真正的 API 请求发生在 run_agent 内部

    print("repo-agent started")  # 提示用户程序已经启动
    print(f"target repo: {repo_path}")  # 显示 Agent 将要读取的仓库

    while True:  # 不断循环，让用户可以连续输入问题
        question = input("repo_agent> ")  # 等待输入并保存到 question

        if question == "/exit":  # 判断用户是否要求退出
            print("bye")  # 输出退出提示
            break  # 跳出 while 循环，结束程序

        if question == "/list":  # 判断用户是否输入了查看仓库目录的命令
            entries = list_files(repo_path)  # 调用工具，并接收工具返回的列表

            for entry in entries:  # 逐个取得列表中的文件名或文件夹名
                print(f"- {entry}")  # 将当前名称打印到终端

            continue  # 本轮处理完成，回到循环开头等待下一次输入

        if question.startswith("/read "):  # 判断输入是否以“/read加空格”开头
            relative_path = question.removeprefix("/read ").strip()  # 删除命令部分，只保留文件路径

            try:  # 尝试调用工具读取文件
                content = read_file(repo_path, relative_path)  # 调用工具读取文件内容
            except ValueError as error:  # 接住读取工具主动抛出的预期错误
                print(f"error: {error}")  # 将错误原因显示给用户
                continue  # 本轮结束，回到循环开头继续等待输入

            print(content)  # 将工具返回的文件内容显示到终端
            continue  # 本轮处理结束，等待下一次输入

        if question.startswith("/search "):  # 判断用户是否输入搜索命令
            query = question.removeprefix("/search ").strip()  # 删除命令部分，取得关键词

            if not query:  # 检查关键词是否为空
                print("error: search query is required")  # 提示必须提供关键词
                continue  # 回到循环开头等待下一次输入

            matches = search_text(repo_path, query)  # 调用搜索工具并取得匹配列表

            if not matches:  # 判断搜索结果是否为空
                print("no matches")  # 告诉用户没有找到结果
                continue  # 回到循环开头等待下一次输入

            for match in matches[:20]:  # 只取前 20 条结果，避免输出过多
                print(f"- {match}")  # 输出文件路径、行号和匹配文本

            if len(matches) > 20:  # 判断实际结果是否超过 20 条
                print(f"showing 20 of {len(matches)} matches")  # 显示总结果数量

            continue  # 搜索处理完成，等待下一次输入

        answer = run_agent(  # 普通自然语言输入交给 Agent loop 处理
            repo_path=repo_path,  # 限制 Agent 只能读取指定仓库
            question=question,  # 传入用户当前问题
            router=router,  # 复用 CLI 启动时创建的模型路由
        )
        print(answer)  # 输出 Agent 根据仓库真实内容生成的最终回答
