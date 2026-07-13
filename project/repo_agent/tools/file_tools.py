from pathlib import Path #导入Path 用于接收仓库文件夹路径

#括号内是 参数名 参数类型  返回一个列表 列表内都是字符串
def list_files(repo_path: Path) -> list[str]:  # 定义工具：输入 Path，返回字符串列表
    entries = []  # 创建空列表，用来保存发现的文件名和文件夹名

    #把repo_path 中的每样东西挨个取出来 每次取一个叫做 entry  iterdir 
    #iterdir iterater遍历逐个过一遍 dir文件夹 把这个文件夹里的东西一个个列出来
    for entry in repo_path.iterdir():  # 逐个读取仓库根目录下的内容
        if entry.is_dir():  # 判断当前内容是不是文件夹
            entries.append(f"{entry.name}/")  # 文件夹名称后面添加斜杠
        else:  # 如果不是文件夹，就把它当作文件处理
            entries.append(entry.name)  # 将文件名加入结果列表
            #是文件夹加个/ 不是文件夹直接加入

    entries.sort()  # 按名称排序，让每次输出顺序保持稳定
    return entries

def read_file(repo_path: Path, relative_path: str) -> str:  # 定义读取文本文件的工具
    repo_root = repo_path.resolve()  # 确保仓库根目录是完整绝对路径
    #左边是repopath 连接上 relativepath就是实际文件的地址
    file_path = (repo_root / relative_path).resolve()  # 将仓库路径与文件相对路径连接起来

    if not file_path.is_relative_to(repo_root):  # 检查目标文件是否仍在仓库内部
        raise ValueError("file path must stay inside the repository")  # 越界就报错并停止读取

    if not file_path.is_file():  # 检查目标路径是否是一个真实存在的文件
        raise ValueError(f"file not found: {relative_path}")  # 文件不存在就报错

    return file_path.read_text(encoding="utf-8")  # 使用 UTF-8 读取文本并返回字符串

def search_text(repo_path: Path, query: str) -> list[str]:  # 定义搜索工具，返回匹配文件路径列表
    repo_root = repo_path.resolve()  # 将仓库根目录转换为绝对路径
    matches = []  # 创建空列表，用来保存匹配的文件路径

    for file_path in repo_root.rglob("*.py"):  # 递归寻找仓库repopath中的所有 Python 文件  每个都叫做filepath
        resolved_path = file_path.resolve()  # 将当前文件路径转换成绝对路径

        if not resolved_path.is_relative_to(repo_root):  # 检查文件是否仍在仓库内部
            continue  # 如果文件跑到仓库外部，就跳过当前文件

        try:  # 尝试读取当前 Python 文件
            content = resolved_path.read_text(encoding="utf-8")  # 读取文件的全部文本

        except UnicodeDecodeError:  # 如果文件不是有效的 UTF-8 文本
            continue  # 跳过当前文件，继续检查下一个文件

        relative_path = resolved_path.relative_to(repo_root)  # 取得当前文件的仓库相对路径

        lines = content.splitlines()  # 将完整文件内容拆成一行一行的字符串列表
        #enumerate给他一个列表 从1开始编号 普通for一次拿一个但是enumerate之后每次拿两个
        for line_number, line in enumerate(lines, start=1):  # 同时取得行号和当前行文本
            if query.lower() in line.lower():  # 忽略大小写，检查当前行是否包含关键词
                snippet = line.strip()  # 删除当前行开头和结尾的多余空格
                match = f"{relative_path}:{line_number}: {snippet}"  # 组合搜索结果
                matches.append(match)  # 将当前匹配结果加入列表

    matches.sort()  # 按路径名称排序，让输出顺序保持稳定
    return matches  # 返回所有匹配文件的相对路径
