"""验证目录分析的结果状态、错误边界和扫描规则。"""

import tokenize
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TextIO
from unittest.mock import patch

from repotrail.analysis.repository import analyze_repository


class AnalyzeRepositoryTests(unittest.TestCase):
    def test_reports_mixed_file_results(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "good.py").write_text(
                "def run():\n    pass\n",
                encoding="utf-8",
            )
            (root / "broken.py").write_text(
                "def broken(:\n",
                encoding="utf-8",
            )
            (root / "empty.py").write_text("", encoding="utf-8")
            (root / "app.ts").write_text("", encoding="utf-8")
            (root / "README.md").write_text(
                "# demo",
                encoding="utf-8",
            )

            result = analyze_repository(root)

            self.assertEqual(
                result["root"],
                root.absolute().as_posix(),
            )

            # 验证顺序、语言分类和三种状态。
            # broken.py 失败后，后面的文件仍应完成。
            self.assertEqual(
                [
                    (r["path"], r["language"], r["status"])
                    for r in result["files"]
                ],
                [
                    ("README.md", None, "unsupported"),
                    ("app.ts", "typescript", "unsupported"),
                    ("broken.py", "python", "failed"),
                    ("empty.py", "python", "parsed"),
                    ("good.py", "python", "parsed"),
                ],
            )

            # 按相对路径建立临时字典，方便检查各文件结果。
            records = {
                r["path"]: r
                for r in result["files"]
            }

            self.assertIsNone(records["app.ts"]["graph"])
            self.assertIsNone(records["broken.py"]["graph"])
            self.assertTrue(records["broken.py"]["message"])

            good_graph = records["good.py"]["graph"]
            assert good_graph is not None

            self.assertEqual(
                good_graph["nodes"][1]["name"],
                "run",
            )
            self.assertIsNone(records["good.py"]["message"])

            # 空 Python 文件也是分析成功，图谱只包含文件节点。
            empty_graph = records["empty.py"]["graph"]
            assert empty_graph is not None

            self.assertEqual(len(empty_graph["nodes"]), 1)
            self.assertEqual(empty_graph["edges"], [])

    def test_empty_repository_returns_empty_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            self.assertEqual(
                analyze_repository(root),
                {
                    "root": root.absolute().as_posix(),
                    "files": [],
                },
            )

    def test_invalid_root_raises(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "single.py"
            file.write_text("", encoding="utf-8")

            # 无效根目录不能被伪装成“空目录分析成功”。
            for path, error_type in (
                (root / "missing", FileNotFoundError),
                (file, NotADirectoryError),
            ):
                with self.subTest(path=path), self.assertRaises(error_type):
                    analyze_repository(path)

    def test_source_encoding_and_decode_errors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "legacy.py").write_bytes(
                "# coding: latin-1\ndef café():\n    pass\n".encode(
                    "latin-1"
                )
            )
            (root / "invalid.py").write_bytes(
                b"# comment\nvalue = '\xff'\n"
            )

            records = {
                r["path"]: r
                for r in analyze_repository(root)["files"]
            }

            self.assertEqual(
                records["legacy.py"]["status"],
                "parsed",
            )
            graph = records["legacy.py"]["graph"]
            assert graph is not None

            self.assertEqual(graph["nodes"][1]["name"], "café")
            self.assertEqual(
                records["invalid.py"]["status"],
                "failed",
            )
            self.assertIsNone(records["invalid.py"]["graph"])

    def test_file_permission_error_does_not_stop_other_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "denied.py").write_text("", encoding="utf-8")
            (root / "good.py").write_text("", encoding="utf-8")

            # 保存原函数，模拟器遇到正常文件时仍使用真实读取。
            original_open = tokenize.open

            def open_source(path: Path) -> TextIO:
                if path.name == "denied.py":
                    raise PermissionError("无权读取 denied.py")
                return original_open(path)

            # 仅模拟一个文件无法读取，避免依赖当前用户的实际权限。
            with patch(
                "repotrail.analysis.repository.tokenize.open",
                side_effect=open_source,
            ):
                result = analyze_repository(root)

            self.assertEqual(
                [
                    (r["path"], r["status"])
                    for r in result["files"]
                ],
                [
                    ("denied.py", "failed"),
                    ("good.py", "parsed"),
                ],
            )
            self.assertIn(
                "无权读取",
                result["files"][0]["message"] or "",
            )

    def test_reuses_scanner_filters_and_skips_links(self) -> None:
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()

            for name in (
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
            ):
                ignored = root / name
                ignored.mkdir()
                (ignored / "hidden.py").write_text(
                    "",
                    encoding="utf-8",
                )

            outside = base / "outside.py"
            outside.write_text("", encoding="utf-8")

            (root / "linked.py").symlink_to(outside)
            (root / "keep.py").write_text("", encoding="utf-8")

            result = analyze_repository(root)

            self.assertEqual(
                [r["path"] for r in result["files"]],
                ["keep.py"],
            )