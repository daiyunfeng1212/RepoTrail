"""命令行参数处理"""

import argparse
import sys
from pathlib import Path

from repotrail import __version__
from repotrail.languages import detect_language
from repotrail.scanner import scan_files


def main(argv: list[str] | None = None) -> int:
    """运行CLI：成功返回0，失败返回1。

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

    # 解析参数
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

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
