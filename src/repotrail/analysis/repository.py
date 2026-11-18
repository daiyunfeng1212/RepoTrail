"""协调目录扫描、文件结构分析和跨文件依赖分析。"""

import tokenize
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from repotrail.analysis.graph import FileGraph, build_file_graph
from repotrail.analysis.import_resolution import resolve_import
from repotrail.analysis.languages import detect_language
from repotrail.analysis.python_parser import (
    PythonImport,
    extract_python_structure,
    extract_python_symbols,
)
from repotrail.analysis.scanner import scan_files


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


class ImportEdge(TypedDict):
    """有源码导入声明作为证据的文件依赖边。端点均为相对路径。"""

    source: str
    target: str
    kind: Literal["imports"]
    declaration: PythonImport


class UnresolvedImport(TypedDict):
    """无法在扫描范围内定位来源模块的导入声明。"""

    source: str
    declaration: PythonImport


class ImportDependencies(TypedDict):
    """按文件及源码顺序排列的已定位依赖与未解析声明。"""

    edges: list[ImportEdge]
    unresolved: list[UnresolvedImport]


class RepositoryAnalysis(TypedDict):
    """一次目录分析结果，文件记录保持扫描器给出的路径顺序。"""

    root: str
    files: list[FileAnalysis]
    dependencies: NotRequired[ImportDependencies]


def analyze_repository(
    root: Path,
    *,
    include_dependencies: bool = False,
) -> RepositoryAnalysis:
    """顺序分析目录中的文件，不修改或执行源码。

    Python 文件生成结构图。
    其他类型保留记录，标记为结构分析未支持。
    include_dependencies 启用静态导入分析，以 root 作为 Python 导入根目录。

    单文件读取、编码或解析失败会记录原因并继续。
    根目录无效或扫描失败时，向调用方传播文件系统异常。
    """
    # 统一路径表示。
    # 根目录有效性检查、忽略目录和符号链接规则由扫描器负责。
    root = root.absolute()
    paths = scan_files(root)

    files: list[FileAnalysis] = []
    dependencies: ImportDependencies | None = None
    if include_dependencies:
        dependencies = {"edges": [], "unresolved": []}
    indexed_files = set(paths) if include_dependencies else set()

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

                if dependencies is None:
                    symbols = extract_python_symbols(source)
                    imports = []
                else:
                    symbols, imports = extract_python_structure(source)

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

                if dependencies is not None:
                    for declaration in imports:
                        target = resolve_import(relative_path, declaration, indexed_files)
                        if target is None:
                            dependencies["unresolved"].append(
                                {"source": record["path"], "declaration": declaration}
                            )
                        else:
                            dependencies["edges"].append(
                                {
                                    "source": record["path"],
                                    "target": target.as_posix(),
                                    "kind": "imports",
                                    "declaration": declaration,
                                }
                            )

        files.append(record)

    report: RepositoryAnalysis = {
        "root": root.as_posix(),
        "files": files,
    }
    if dependencies is not None:
        report["dependencies"] = dependencies
    return report
