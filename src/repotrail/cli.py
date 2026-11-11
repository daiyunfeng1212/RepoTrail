"""命令行入口：当前只负责展示帮助和版本。"""
import argparse

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='repotrail',
        description='RepoTrail · 代码路标：多语言仓库导读工具（当前为最小脚手架）。',
        epilog='当前尚未实现仓库扫描、代码解析和可视化。',
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.parse_args(argv)
    parser.print_help()
    return 0
