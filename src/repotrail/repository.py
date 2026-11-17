"""协调目录扫描、语言识别和单文件结构分析。"""

import tokenize
from pathlib import Path
from typing import Literal, TypedDict

from repotrail.graph import FileGraph, build_file_graph
from repotrail.languages import detect_language
from repotrail.python_parser import extract_python_symbols
from repotrail.scanner import scan_files


class FileAnalysis(TypedDict):
    """单个文件的结构分析结果。

    path 是相对仓库根目录的路径。
    graph 只在 parsed 状态下提供。
    message 保存未支持的说明或失败原因，成功时为 None。
    """

    path: str
    language: str | None
    status: Literal["parsed", "unsupported", "failed"]
    graph: FileGraph | None
    message: str | None


class RepositoryAnalysis(TypedDict):
    """一次目录分析结果，文件记录保持扫描器给出的路径顺序。"""

    root: str
    files: list[FileAnalysis]


def analyze_repository(root: Path) -> RepositoryAnalysis:
    """顺序分析目录中的文件，不修改或执行源码。

    Python 文件生成结构图。
    其他类型保留记录，标记为结构分析未支持。

    单文件读取、编码或解析失败会记录原因并继续。
    根目录无效或扫描失败时，向调用方传播文件系统异常。
    """
    # 统一路径表示。
    # 根目录有效性检查、忽略目录和符号链接规则由扫描器负责。
    root = root.absolute()
    paths = scan_files(root)

    files: list[FileAnalysis] = []

    for relative_path in paths:
        language = detect_language(relative_path)

        # 非 Python 文件使用这个明确的分类结果。
        # Python 文件则在下面根据实际执行结果转为 parsed 或 failed。
        record: FileAnalysis = {
            "path": relative_path.as_posix(),
            "language": language,
            "status": "unsupported",
            "graph": None,
            "message": "当前尚未支持该文件的结构分析。",
        }

        if language == "python":
            path = root / relative_path

            try:
                with tokenize.open(path) as source_file:
                    source = source_file.read()

                symbols = extract_python_symbols(source)

            except (OSError, SyntaxError, UnicodeError) as error:
                # 只处理预期的单文件输入错误。
                # 记录原因后，循环仍会继续处理其他文件。
                record["status"] = "failed"
                record["message"] = str(error)

            else:
                # else 只在 try 正常完成、没有抛出异常时执行。
                #
                # 图谱构建错误属于内部问题，保留原始异常供定位，
                # 不把程序错误伪装成普通文件读取失败。
                record["graph"] = build_file_graph(path, symbols)
                record["status"] = "parsed"
                record["message"] = None

        files.append(record)

    return {
        "root": root.as_posix(),
        "files": files,
    }
