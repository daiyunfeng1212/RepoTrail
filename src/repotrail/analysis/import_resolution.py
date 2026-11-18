"""根据已扫描的文件定位 Python 相对导入的来源模块。"""

from collections.abc import Set as AbstractSet
from pathlib import Path

from repotrail.analysis.python_parser import PythonImport


def resolve_relative_import(
    source_file: Path,
    declaration: PythonImport,
    indexed_files: AbstractSet[Path],
) -> Path | None:
    """返回相对导入来源模块的路径，无法定位时返回 None。

    source_file 和 indexed_files 均相对于同一个 Python 导入根目录，
    declaration 来自 extract_python_imports()。仅查询已扫描的文件。
    """
    level = declaration["level"]
    packages = source_file.parents
    # 一个点使用当前包。导入根目录本身没有包名，不能跨到这一层。
    if not 0 < level < len(packages):
        return None

    package = packages[level - 1]
    module = declaration["module"]
    if module is None:
        # `from . import name` 的来源是包，name 可能是属性或子模块。
        initializer = package / "__init__.py"
        return initializer if initializer in indexed_files else None

    parts = module.split(".")
    for part in parts[:-1]:
        package = package / part
        # 有同名普通模块时，只有显式包入口能支持继续向下定位。
        if (
            package.with_suffix(".py") in indexed_files
            and package / "__init__.py" not in indexed_files
        ):
            return None

    target = package / parts[-1]
    initializer = target / "__init__.py"
    if initializer in indexed_files:
        return initializer

    module_file = target.with_suffix(".py")
    return module_file if module_file in indexed_files else None
