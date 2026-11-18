"""验证从 Python 静态导入声明定位已扫描的文件。"""

import unittest
from pathlib import Path

from repotrail.analysis.import_resolution import resolve_relative_import
from repotrail.analysis.python_parser import extract_python_imports


class RelativeImportResolutionTests(unittest.TestCase):
    def test_locates_modules_using_the_source_package_and_relative_level(self) -> None:
        source = Path("pkg/feature/main.py")
        indexed = {
            source,
            Path("pkg/feature/utils.py"),
            Path("pkg/utils.py"),
            Path("pkg/shared/tools.py"),
        }
        declarations = extract_python_imports(
            "from .utils import load\n"
            "from ..utils import load as read\n"
            "from ..shared.tools import run\n"
        )

        self.assertEqual(
            [
                resolve_relative_import(source, declaration, indexed)
                for declaration in declarations
            ],
            [
                Path("pkg/feature/utils.py"),
                Path("pkg/utils.py"),
                Path("pkg/shared/tools.py"),
            ],
        )

    def test_prefers_package_initializer_and_does_not_guess_imported_name(self) -> None:
        source = Path("pkg/main.py")
        indexed = {
            source,
            Path("pkg/__init__.py"),
            Path("pkg/utils.py"),
            Path("pkg/utils/__init__.py"),
        }
        declarations = extract_python_imports(
            "from .utils import load\nfrom . import utils\n"
        )

        self.assertEqual(
            [
                resolve_relative_import(source, declaration, indexed)
                for declaration in declarations
            ],
            [Path("pkg/utils/__init__.py"), Path("pkg/__init__.py")],
        )

    def test_leaves_missing_out_of_scope_and_ambiguous_imports_unresolved(self) -> None:
        indexed = {
            Path("main.py"),
            Path("pkg/main.py"),
            Path("pkg/utils.py"),
            Path("pkg/utils/sub.py"),
            Path("utils.py"),
            Path("other/missing.py"),
        }
        for source, statement in (
            ("pkg/main.py", "from .missing import load"),
            ("pkg/main.py", "from ..utils import load"),
            ("main.py", "from .utils import load"),
            ("pkg/main.py", "import utils"),
            ("pkg/main.py", "from . import utils"),
            ("pkg/main.py", "from .utils.sub import load"),
        ):
            with self.subTest(source=source, statement=statement):
                (declaration,) = extract_python_imports(statement)
                self.assertIsNone(
                    resolve_relative_import(Path(source), declaration, indexed)
                )
