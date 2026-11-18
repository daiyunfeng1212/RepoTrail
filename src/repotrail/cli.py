"""处理命令行参数，调用源码提取和目录分析。"""

import argparse
import json
import sys
import tokenize
from pathlib import Path

from repotrail import __version__
from repotrail.analysis.graph import build_file_graph
from repotrail.analysis.languages import detect_language
from repotrail.analysis.python_parser import (
    extract_python_imports,
    extract_python_symbols,
)
from repotrail.analysis.repository import analyze_repository
from repotrail.analysis.scanner import scan_files


def main(argv: list[str] | None = None) -> int:
    """运行 CLI：成功返回 0，读取或分析失败返回 1。

    argv 为 None 时读取终端参数，也可以传入参数列表。
    参数错误由 argparse 报告并以退出码 2 结束；
    显示帮助和版本以退出码0结束。
    """
    parser = argparse.ArgumentParser(
        prog="repotrail",
        description="帮助开发者理解陌生代码库。",
    )

    # 注册 --version 参数
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示程序版本信息并退出。",
    )

    # 子命令用于区分用户想执行的操作。
    # dest ="command" 表示把所选子命令保存在 args.command 中。
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # 注册 scan 子命令
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描仓库中的候选文件",
        description="递归扫描目录，跳过忽略目录和符号链接。",
    )

    scan_parser.add_argument("path", type=Path, help="要扫描的目录路径")

    # store_true 将开关默认设为 False，传入参数时设为 True。
    # 参数名中的连字符会转为下划线，因此通过 args.show_language 访问。
    scan_parser.add_argument(
        "--show-language",
        action="store_true",
        help="显示根据扩展名推断的候选语言。",
    )

    # parse 使用独立的参数解析器，与 scan 的开关相互独立。
    parse_parser = subparsers.add_parser(
        "parse",
        help="提取单个 Python 文件中的类与函数定义。",
    )

    parse_parser.add_argument(
        "path", 
        type=Path, 
        help="要分析的 .py 文件路径。"
        )

    # 默认继续显示简单名称，传入开关后显示外层类、函数组成的限定名。
    parse_parser.add_argument(
        "--qualified-names",
        action="store_true",
        help="显示包含外层类、函数的限定名。(仅限文本输出)。",
    )

    # choices 限制合法值，输入由argparse报告参数错误。
    # default 保持已有命令的默认行为。
    parse_parser.add_argument(
        "--format",
        choices=("text","json"),
        default="text",
        help="输出格式，默认text。"
    )

    # graph 固定输出图谱JSON,拥有独立的参数集合。
    graph_parser = subparsers.add_parser(
        "graph",
        help="生成单个python文件的包含关系图谱JSON。",
    )

    graph_parser.add_argument(
        "path",
        type=Path,
        help="要分析的 .py 文件路径。",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="分析目录并输出包含逐文件状态的 JSON 报告。",
    )
    analyze_parser.add_argument("path", type=Path, help="要分析的目录路径。")

    imports_parser = subparsers.add_parser(
        "imports",
        help="提取 Python 文件中的导入声明并输出 JSON。",
    )
    imports_parser.add_argument("path", type=Path, help="要分析的 .py 文件路径。")

    # 解析参数
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0


    if args.command == "scan":
        try:
            files = scan_files(args.path)
        except OSError as error:
            print(f"扫描失败：{error}", file=sys.stderr)
            return 1

        for file in files:
            if args.show_language:
                # 分类只依赖路径名称，可以直接使用扫描返回的相对路径。
                language = detect_language(file)
                # 未识别文件仍保留，文档和配置也可能对理解仓库有价值。
                if language is None:
                    language = "unknown"
                # 制表符分隔语言和路径两列，文件顺序仍由扫描结果决定。
                print(f"{language}\t{file.as_posix()}")
            else:
                print(file.as_posix())

        print(f"共{len(files)}个文件。")
        return 0

    if args.command == "analyze":
        try:
            report = analyze_repository(args.path)
        except OSError as error:
            print(f"目录分析失败：{error}", file=sys.stderr)
            return 1

        # 退出码表示报告是否生成，单个文件的错误由报告中的状态表示。
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    # 单文件命令共享文件类型检查、源码读取和输入错误处理。
    # 分类决定能否选择 Python 解析器，读取和解析阶段再检查实际内容。
    if detect_language(args.path) != "python":
        print("解析失败：目前仅支持扩展名为 .py 的 Python 文件。", file=sys.stderr)
        return 1

    try:
        # tokenize.open 以只读方式打开源码，遵循 BOM 和 coding 编码声明。
        # with 保证读取完成或发生异常时，文件句柄都会关闭。
        with tokenize.open(args.path) as source_file:
            source = source_file.read()
        if args.command == "imports":
            imports = extract_python_imports(source)
        else:
            symbols = extract_python_symbols(source)
    except (OSError, SyntaxError, UnicodeError) as error:
        # 覆盖文件系统错误、编码声明或解析错误，以及文本解码错误。
        # 预期输入错误转为提示，其他编程错误继续抛出。
        print(f"解析失败：{error}", file=sys.stderr)
        return 1

    if args.command == "imports":
        import_report = {
            "file": args.path.absolute().as_posix(),
            "language": "python",
            "imports": imports,
        }
        print(json.dumps(import_report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "graph":
        graph = build_file_graph(args.path,symbols)
        print(json.dumps(graph,ensure_ascii=False,indent=2))
        return 0

    if args.format == "json":
        # absolute() 将相对路径转换为绝对路径，不解析符号链接。
        # as_posix() 使用 / 表示路径分隔符。
        #
        # 显式声明导出字段，控制对外数据格式。
        # qualified_name、parent_name 是计算属性，也需要主动加入。
        document = {
            "file": args.path.absolute().as_posix(),
            "language": "python",
            "symbols": [
                {
                    "name": symbol.name,
                    "kind": symbol.kind,

                    # Python 中使用元组保存作用域；
                    # 导出时明确转换成列表，对应 JSON 数组。
                    "scope": list(symbol.scope),

                    "qualified_name": symbol.qualified_name,
                    "parent_name": symbol.parent_name,
                    "start_line": symbol.start_line,
                    "end_line": symbol.end_line,
                }
                for symbol in symbols
            ],
        }

        # dumps() 把字典、列表等基本结构转换成 JSON 字符串。
        # ensure_ascii=False 保留中文字符，不转换成 Unicode 转义。
        # indent=2 使用两空格缩进，方便直接查看。
        print(json.dumps(document, ensure_ascii=False, indent=2))

        # JSON 输出后直接返回，不能继续追加“共几个定义”等文本。
        # 否则整个标准输出就不再是合法 JSON。
        return 0
    # 完整提取成功后再输出，避免展示不完整的分析结果。
    # 行号从 1 开始，结束行包含在定义范围内。
    for symbol in symbols:
        name = symbol.qualified_name if args.qualified_names else symbol.name
        print(f"{symbol.kind}\t{name}\t{symbol.start_line}:{symbol.end_line}")
    print(f"共{len(symbols)}个定义。")
    return 0
