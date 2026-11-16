"""收集仓库中的候选文件"""

import stat
from pathlib import Path

IGNORED_DIRS = [".git", "node_modules", "__pycache__",".venv"]

def scan_files(root: Path) -> list[Path]:
    """返回排序后的相对文件路径，跳过忽略目录和符号链接。

    root 是待扫描目录;根目录会解析为绝对路径，
    遍历时跳过忽略目录、符号链接和其他非普通文件。

    路径不存在时抛出 FileNotFoundError，输入为文件时抛出
    NotADirectoryError，权限等文件系统错误向调用方传播。
    """
    # 获取根目录的绝对路径
    root = root.resolve(strict=True)

    if not stat.S_ISDIR(root.stat().st_mode):
        raise NotADirectoryError(f"扫描路径不是目录：{root}")

    pending = [root]

    files: list[Path] = []

    while pending:

        current = pending.pop()

        for entry in current.iterdir():

            entry_mode = entry.stat(follow_symlinks=False).st_mode

            if stat.S_ISDIR(entry_mode):
                if entry.name not in IGNORED_DIRS:
                    pending.append(entry)

            elif stat.S_ISREG(entry_mode):
                # relative_to 返回相对于 root 的相对路径
                # /repo/src/main.py -> src/main.py
                files.append(entry.relative_to(root))

    return sorted(files,key= lambda path: path.as_posix())

