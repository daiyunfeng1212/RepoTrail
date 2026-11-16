"""命令行参数处理"""

import argparse
import sys
from pathlib import Path

from repotrail import __version__
from repotrail.scanner import scan_files


def main(argv: list[str] | None = None) -> int:
    """运行CLI：成功返回0，失败返回1。

    argv 为 None 时读取终端参数，也可以传入参数列表。
    参数错误由argparses报告并以退出码2结束;
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
    subparsers = parser.add_subparsers(dest="command", title="子命令")

    # 注册 scan 子命令
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描仓库中的候选文件",
        description="递归扫描目录，跳过忽略目录和符号链接。",
    )

    scan_parser.add_argument("path", type=Path, help="要扫描的目录路径")

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
        print(file.as_posix())

    print(f"共{len(files)}个文件。")

    return 0
