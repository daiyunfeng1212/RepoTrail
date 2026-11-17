"""根据路径扩展名识别候选编程语言。"""

from pathlib import Path

LANGUAGE_BY_SUFFIX = {
    ".py":"python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
}

def detect_language(path: Path) -> str | None:
    """返回已知扩展名对应的语言名称，无法识别时返回None。

    只根据路径名称判断，不要求文件存在，也不读取文件内容。
    扩展名忽略大小写；仅使用最后一个扩展名。
    """

    suffix = path.suffix.lower()

    return LANGUAGE_BY_SUFFIX.get(suffix)