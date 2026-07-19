import json
from pathlib import Path
from typing import cast, get_args

from .schemas import EvaluationCase, EvaluationCategory


# JSONL 中每道评测题必须包含的全部字段
REQUIRED_CASE_KEYS = {
    "case_id",
    "repository",
    "question",
    "expected_files",
    "expected_symbols",
    "category",
}

# 从 Literal 类型中取得运行时允许使用的四个类别字符串
VALID_CATEGORIES = set(get_args(EvaluationCategory))


# 表示评测数据本身不符合项目规定的格式
class EvaluationDataError(ValueError):
    pass


# 检查 json.loads() 返回的一个对象，并在成功后把它视为 EvaluationCase
def validate_evaluation_case(
    data: object,
    source: Path,
    line_number: int,
) -> EvaluationCase:
    # 报错时同时指出文件和行号，方便定位 JSONL 中的具体题目
    location = f"{source}:{line_number}"

    # 每一行 JSON 必须是对象；JSON object 解析到 Python 后就是字典
    if not isinstance(data, dict):
        raise EvaluationDataError(f"{location}: evaluation case must be an object")

    # 找出 schema 要求但当前字典没有提供的字段
    missing = REQUIRED_CASE_KEYS - data.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise EvaluationDataError(f"{location}: missing fields: {names}")

    # 找出 schema 没有声明但当前字典额外提供的字段
    unexpected = data.keys() - REQUIRED_CASE_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise EvaluationDataError(f"{location}: unexpected fields: {names}")

    # 稳定 ID 必须存在且有内容，不能依赖会变化的 JSONL 行号
    case_id = data["case_id"]
    if not isinstance(case_id, str) or not case_id.strip():
        raise EvaluationDataError(f"{location}: case_id must be a non-empty string")

    # 仓库名称用于让 Runner 选择对应的源码快照
    repository = data["repository"]
    if not isinstance(repository, str) or not repository.strip():
        raise EvaluationDataError(
            f"{location}: repository must be a non-empty string"
        )

    # 问题必须是非空字符串，避免产生没有实际问题的评测题
    question = data["question"]
    if not isinstance(question, str) or not question.strip():
        raise EvaluationDataError(f"{location}: question must be a non-empty string")

    # 正确文件必须是非空列表，并且列表中的每一项都必须是非空字符串
    expected_files = data["expected_files"]
    if (
        not isinstance(expected_files, list)
        or not expected_files
        or not all(isinstance(item, str) and item.strip() for item in expected_files)
    ):
        raise EvaluationDataError(
            f"{location}: expected_files must be a non-empty list of strings"
        )

    # 正确符号可以是空列表，但列表中的已有项目都必须是非空字符串
    expected_symbols = data["expected_symbols"]
    if not isinstance(expected_symbols, list) or not all(
        isinstance(item, str) and item.strip() for item in expected_symbols
    ):
        raise EvaluationDataError(
            f"{location}: expected_symbols must be a list of strings"
        )

    # 类别必须属于 schemas.py 中 Literal 声明的四种值之一
    category = data["category"]
    if category not in VALID_CATEGORIES:
        allowed = ", ".join(sorted(VALID_CATEGORIES))
        raise EvaluationDataError(
            f"{location}: category must be one of: {allowed}"
        )

    # 上面的运行时检查已经完成；cast 只把这一事实告诉类型检查器
    return cast(EvaluationCase, data)


# 逐行读取 JSONL 文件，返回全部已经通过运行时校验的评测题
def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []#这里的列表内容被schemas限制
    #所以就是schemas组成的列表
    seen_case_ids: set[str] = set()
    # 使用 UTF-8 打开数据文件，with 代码块结束后文件会自动关闭
    with path.open("r", encoding="utf-8") as file:
        # enumerate(..., start=1) 让行号从人类习惯的 1 开始
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            # JSONL 要求每一行都是完整 JSON，因此空行也视为数据错误
            if not line:
                raise EvaluationDataError(f"{path}:{line_number}: line must not be empty")

            try:
                # 把当前 JSON 字符串解析成 Python 字典、列表或其他基础值
                data = json.loads(line)
            except json.JSONDecodeError as error:
                # 转成项目异常，并保留原始异常作为错误原因
                raise EvaluationDataError(
                    f"{path}:{line_number}: invalid JSON: {error.msg}"
                ) from error

            # 先校验当前对象，再用稳定 ID 检查整份题库是否出现重复题号
            case = validate_evaluation_case(
                data=data,
                source=path,
                line_number=line_number,
            )

            case_id = case["case_id"]
            if case_id in seen_case_ids:
                raise EvaluationDataError(
                    f"{path}:{line_number}: duplicate case_id: {case_id}"
                )

            seen_case_ids.add(case_id)
            cases.append(case)

    return cases


def validate_evaluation_evidence(
    cases: list[EvaluationCase],
    repo_paths: dict[str, Path],
) -> None:
    """确认每道题记录的标准文件和标准符号仍存在于目标仓库。"""

    for case in cases:
        case_id = case["case_id"]
        repository = case["repository"]
        if repository not in repo_paths:
            raise EvaluationDataError(
                f"{case_id}: repository is not configured: {repository}"
            )

        repo_root = repo_paths[repository].resolve()
        evidence_paths: list[Path] = []

        for relative_path in case["expected_files"]:
            evidence_path = (repo_root / relative_path).resolve()
            if not evidence_path.is_relative_to(repo_root):
                raise EvaluationDataError(
                    f"{case_id}: expected file escapes repository: {relative_path}"
                )
            if not evidence_path.is_file():
                raise EvaluationDataError(
                    f"{case_id}: expected file not found: {relative_path}"
                )
            evidence_paths.append(evidence_path)

        try:
            evidence_texts = [
                evidence_path.read_text(encoding="utf-8", errors="ignore")
                for evidence_path in evidence_paths
            ]
        except OSError as error:
            raise EvaluationDataError(
                f"{case_id}: cannot read expected evidence"
            ) from error

        for symbol in case["expected_symbols"]:
            if not any(symbol in text for text in evidence_texts):
                raise EvaluationDataError(
                    f"{case_id}: expected symbol not found: {symbol}"
                )
