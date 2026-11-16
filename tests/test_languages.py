"""验证候选语言识别的别名和输入边界"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repotrail.languages import detect_language

class DetectLanguageTests(unittest.TestCase):
    def test_recognizes_language_aliases(self)->None:
        cases = [
            ("app.js","javascript"),
            ("view.jsx","javascript"),
            ("app.ts","typescript"),
            ("view.tsx","typescript"),
        ]

        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(detect_language(Path(filename)), expected)

    def test_extension_matching_ignores_case(self) -> None:
        # 目录部分不影响识别，扩展名大小写也不影响结果。
        self.assertEqual(
            detect_language(Path("src/MAIN.PY")),
            "python",
        )

    def test_unknown_or_absent_extension_returns_none(self) -> None:
        # 分别验证：
        # 1. 当前未收录的扩展名；
        # 2. 无扩展名的文件；
        # 3. 点文件；
        # 4. 带代码扩展名的备份文件。
        #
        # source.py.bak 的最终扩展名是 .bak，
        # 应避免因为中间包含 .py 而误判为 Python。
        for filename in (
            "README.md",
            "Dockerfile",
            ".env",
            "source.py.bak",
        ):
            with self.subTest(filename=filename):
                # assertIsNone 专门检查结果是否为 None。
                self.assertIsNone(detect_language(Path(filename)))

    def test_does_not_require_existing_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.py"

            # 只创建了临时目录，没有创建这个文件。
            self.assertFalse(path.exists())

            # 识别只依赖路径名称，文件不存在仍可以分类。
            self.assertEqual(detect_language(path), "python")