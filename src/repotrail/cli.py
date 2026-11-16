"""命令行参数处理"""

import argparse

from repotrail import __version__

def main(argv: list[str] | None = None) -> int:
    """处理命令行参数并返回退出码。"""
    parser = argparse.ArgumentParser(
        prog="repotrail",
        description="帮助开发者理解陌生代码库。",
    )

    # 注册 --version 参数
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示程序版本信息并退出。",
    )

    # 解析参数
    parser.parse_args(argv)

    parser.print_help()
    return 0