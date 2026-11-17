"""通过真实进程验证命令行入口与扫描功能的连接。"""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """启动项目CLI，返回退出码、标准输出和标准错误。"""

        env = os.environ.copy()

        return subprocess.run(
            [sys.executable, "-B", "-m", "repotrail", *args],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            # 测试需要检查失败命令的退出码，因此非零退出时不抛异常。
            check=False,
            timeout=10,
        )

    def test_help(self) -> None:
        # 分别检查默认帮助、总帮助和各子命令帮助。
        for args in ([], ["--help"], ["scan", "--help"], ["parse", "--help"]):
            with self.subTest(args=args):
                result = self.run_cli(args)

                self.assertEqual(result.returncode, 0)
                self.assertIn("usage:", result.stdout)
                self.assertEqual(result.stderr, "")

    def test_version(self) -> None:
        result = self.run_cli(["--version"])

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "repotrail 0.1.0")
        self.assertEqual(result.stderr, "")

    def test_invalid_arguments(self) -> None:
        for args in (["--unknown"], ["scan"], ["parse"], ["unknown"]):
            with self.subTest(args=args):
                result = self.run_cli(args)

                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_scan_prints_relative_paths_and_count(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "b.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")

            result = self.run_cli(["scan", str(root)])

            self.assertEqual(result.returncode, 0)

            # splitlines() 将输出拆分为多行，便于检查路径顺序和数量。
            self.assertEqual(
                result.stdout.splitlines(),
                ["a.py", "src/b.py", "共2个文件。"],
            )
            self.assertEqual(result.stderr, "")

    def test_scan_empty_directory(self) -> None:
        with TemporaryDirectory() as directory:
            result = self.run_cli(["scan", directory])

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "共0个文件。")
            self.assertEqual(result.stderr, "")

    def test_scan_can_show_candidate_languages(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("", encoding="utf-8")
            (root / "view.tsx").write_text("", encoding="utf-8")
            (root / "README.md").write_text("", encoding="utf-8")

            result = self.run_cli(["scan", str(root), "--show-language"])

            self.assertEqual(result.returncode, 0)
            # 检查语言识别已接入命令行，未知类型仍保留并计入总数。
            # 顺序仍按文件路径排列，不因语言分组而改变。
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "unknown\tREADME.md",
                    "python\tapp.py",
                    "typescript\tview.tsx",
                    "共3个文件。",
                ],
            )
            self.assertEqual(result.stderr, "")

    def test_scan_reports_filesystem_errors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "single.py"
            file.write_text("", encoding="utf-8")

            # 两种情况都是扫描失败，应该输出错误并返回 1：
            # 目标路径不存在、目标路径实际是文件。
            for path in (root / "missing", file):
                with self.subTest(path=path):
                    result = self.run_cli(["scan", str(path)])

                    self.assertEqual(result.returncode, 1)
                    self.assertIn("扫描失败：", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_parse_prints_definition_locations_without_executing_source(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(
                "class Service:\n"
                "    def run(self):\n"
                "        return 1\n"
                'raise RuntimeError("源码不应被执行")\n',
                encoding="utf-8",
            )

            result = self.run_cli(["parse", str(path)])

            # 如果执行了目标源码，末尾的 raise 会使命令失败。
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout.splitlines(),
                ["class\tService\t1:3", "function\trun\t2:3", "共2个定义。"],
            )
            self.assertEqual(result.stderr, "")

    def test_parse_source_without_definitions(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            # 空文件和只有变量赋值的文件都应成功，区别于读取或解析失败。
            for source in ("", "value = 1\n"):
                with self.subTest(source=source):
                    path.write_text(source, encoding="utf-8")
                    result = self.run_cli(["parse", str(path)])
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout.strip(), "共0个定义。")
                    self.assertEqual(result.stderr, "")

    def test_parse_respects_declared_source_encoding(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.py"
            source = "# coding: latin-1\ndef café():\n    pass\n"
            # 按 Latin-1 编码保存，确认读取时遵循 coding 声明。
            path.write_bytes(source.encode("latin-1"))

            result = self.run_cli(["parse", str(path)])

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout.splitlines(),
                ["function\tcafé\t2:3", "共1个定义。"],
            )
            self.assertEqual(result.stderr, "")

    def test_parse_reports_input_errors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "folder.py").mkdir()
            (root / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            # 首行有效，后续包含无法按 UTF-8 解码的字节。
            (root / "invalid.py").write_bytes(b"# comment\nvalue = '\xff'\n")
            (root / "wrong_encoding.py").write_text(
                "# coding: not-an-encoding\n", encoding="utf-8"
            )
            (root / "app.js").write_text("", encoding="utf-8")

            for name in (
                "missing.py",
                "folder.py",
                "broken.py",
                "invalid.py",
                "wrong_encoding.py",
                "app.js",
            ):
                with self.subTest(name=name):
                    result = self.run_cli(["parse", str(root / name)])
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("解析失败：", result.stderr)
                    self.assertEqual(result.stdout, "")
