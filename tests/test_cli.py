"""通过真实进程验证命令行入口与扫描功能的连接。"""

import json
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
        for args in (
            [],
            ["--help"],
            ["scan", "--help"],
            ["parse", "--help"],
            ["graph", "--help"],
            ["analyze", "--help"],
            ["imports", "--help"],
        ):
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
        # 子命令缺少路径属于参数错误，应返回 2，而不是帮助用例的 0。
        for args in (
            ["--unknown"],
            ["scan"],
            ["parse"],
            ["graph"],
            ["analyze"],
            ["imports"],
            ["unknown"],
            ["parse", "sample.py", "--format", "yaml"],
        ):
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

    def test_parse_can_show_qualified_names(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(
                "class Service:\n    def run(self):\n        return 1\n",
                encoding="utf-8",
            )

            result = self.run_cli(["parse", str(path), "--qualified-names"])

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout.splitlines(),
                ["class\tService\t1:3", "function\tService.run\t2:3", "共2个定义。"],
            )
            self.assertEqual(result.stderr, "")

    def test_parse_json_exports_definition_fields(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(
                "class 服务:\n    def 运行(self):\n        return 1\n",
                encoding="utf-8",
            )

            # 同时传入限定名开关，验证 JSON 始终导出完整字段。
            result = self.run_cli(
                [
                    "parse",
                    str(path),
                    "--format",
                    "json",
                    "--qualified-names",
                ]
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

            # loads() 将 JSON 字符串还原成 Python 数据结构。
            # 如果输出中混入人类可读的总数，这一步也会失败。
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "file": path.absolute().as_posix(),
                    "language": "python",
                    "symbols": [
                        {
                            "name": "服务",
                            "kind": "class",
                            "scope": [],
                            "qualified_name": "服务",
                            "parent_name": None,
                            "start_line": 1,
                            "end_line": 3,
                        },
                        {
                            "name": "运行",
                            "kind": "function",
                            "scope": ["服务"],
                            "qualified_name": "服务.运行",
                            "parent_name": "服务",
                            "start_line": 2,
                            "end_line": 3,
                        },
                    ],
                },
            )

            # 检查输出保留中文，便于直接查看导出文件。
            self.assertIn("服务.运行", result.stdout)

    def test_parse_json_preserves_empty_result(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "empty.py"
            path.write_text("", encoding="utf-8")

            result = self.run_cli(["parse", str(path), "--format", "json"])

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

            # 无定义仍是成功结果，symbols 应为一个空数组。
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "file": path.absolute().as_posix(),
                    "language": "python",
                    "symbols": [],
                },
            )

    def test_parse_json_failures_leave_stdout_empty(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "broken.py"
            broken.write_text(
                "def valid():\n    pass\ndef broken(:\n",
                encoding="utf-8",
            )

            # 分别验证读取失败和部分源码损坏。
            # 两种情况都不能输出成功或部分 JSON 结果。
            for path in (root / "missing.py", broken):
                with self.subTest(path=path):
                    result = self.run_cli(["parse", str(path), "--format", "json"])

                    self.assertEqual(result.returncode, 1)
                    self.assertIn("解析失败：", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_graph_exports_nodes_and_containment_edges(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(
                "class 服务:\n"
                "    def 运行(self):\n"
                "        return 1\n"
                'raise RuntimeError("源码不应被执行")\n',
                encoding="utf-8",
            )

            result = self.run_cli(["graph", str(path)])

            # 如果执行目标源码，末尾的 raise 会使命令失败。
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

            # 整个标准输出必须是合法 JSON，不能混入文本统计。
            graph = json.loads(result.stdout)

            # set(dict) 返回字典键的集合，检查顶层数据契约。
            self.assertEqual(set(graph), {"nodes", "edges"})

            nodes = graph["nodes"]
            self.assertEqual(len(nodes), 3)
            self.assertEqual(nodes[0]["kind"], "file")
            self.assertEqual(
                nodes[0]["file"],
                path.absolute().as_posix(),
            )
            self.assertEqual(
                [node["qualified_name"] for node in nodes],
                [None, "服务", "服务.运行"],
            )

            # 文件包含类，类包含方法。
            # 使用结果中的 ID 检查连接，不依赖 ID 的具体拼接方式。
            self.assertEqual(
                graph["edges"],
                [
                    {
                        "source": nodes[0]["id"],
                        "target": nodes[1]["id"],
                        "kind": "contains",
                    },
                    {
                        "source": nodes[1]["id"],
                        "target": nodes[2]["id"],
                        "kind": "contains",
                    },
                ],
            )

            self.assertIn("服务.运行", result.stdout)

    def test_graph_empty_source_keeps_file_node(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "empty.py"
            path.write_text("", encoding="utf-8")

            result = self.run_cli(["graph", str(path)])

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

            graph = json.loads(result.stdout)

            # 空文件仍然是仓库中的一个文件，因此保留文件节点。
            self.assertEqual(len(graph["nodes"]), 1)
            self.assertEqual(graph["nodes"][0]["kind"], "file")
            self.assertEqual(graph["edges"], [])

    def test_graph_input_errors_leave_stdout_empty(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            # 前面有完整定义，后面损坏，仍应拒绝输出部分结果。
            (root / "broken.py").write_text(
                "def valid():\n    pass\ndef broken(:\n",
                encoding="utf-8",
            )
            (root / "app.js").write_text("", encoding="utf-8")

            # 分别验证：不存在、解析失败、当前不支持的文件类型。
            for name in ("missing.py", "broken.py", "app.js"):
                with self.subTest(name=name):
                    result = self.run_cli(["graph", str(root / name)])

                    self.assertEqual(result.returncode, 1)
                    self.assertIn("解析失败：", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_imports_exports_declarations_without_loading_modules(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "module.py"
            path.write_text(
                "import os, package.missing as unavailable\n"
                "from ..utils import load as read\n"
                "from . import config\n",
                encoding="utf-8",
            )

            result = self.run_cli(["imports", str(path)])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "file": path.absolute().as_posix(),
                    "language": "python",
                    "imports": [
                        {"module": "os", "name": None, "alias": None, "level": 0, "line": 1},
                        {
                            "module": "package.missing",
                            "name": None,
                            "alias": "unavailable",
                            "level": 0,
                            "line": 1,
                        },
                        {
                            "module": "utils",
                            "name": "load",
                            "alias": "read",
                            "level": 2,
                            "line": 2,
                        },
                        {
                            "module": None,
                            "name": "config",
                            "alias": None,
                            "level": 1,
                            "line": 3,
                        },
                    ],
                },
            )

    def test_imports_returns_empty_list_without_static_declarations(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "module.py"
            path.write_text(
                '# import os\ntext = "from x import y"\n__import__("os")\n',
                encoding="utf-8",
            )

            result = self.run_cli(["imports", str(path)])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout)["imports"], [])

    def test_imports_reports_invalid_input_without_partial_json(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.py").write_text("import os\ndef bad(:\n", encoding="utf-8")
            (root / "module.txt").write_text("import os\n", encoding="utf-8")

            for name in ("broken.py", "missing.py", "module.txt"):
                with self.subTest(name=name):
                    result = self.run_cli(["imports", str(root / name)])

                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("解析失败：", result.stderr)

    def test_analyze_exports_report_with_mixed_file_statuses(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.py").write_text("def bad(:\n", encoding="utf-8")
            (root / "module.py").write_text("def run(): pass\n", encoding="utf-8")
            (root / "notes.md").write_text("# Notes\n", encoding="utf-8")

            result = self.run_cli(["analyze", str(root)])

            # 即使一个文件解析失败，调用方仍应收到完整的目录报告。
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            report = json.loads(result.stdout)
            self.assertEqual(report["root"], root.absolute().as_posix())
            self.assertEqual(
                [(item["path"], item["status"]) for item in report["files"]],
                [
                    ("broken.py", "failed"),
                    ("module.py", "parsed"),
                    ("notes.md", "unsupported"),
                ],
            )
            broken, module, _ = report["files"]
            self.assertTrue(broken["message"])
            self.assertEqual(module["graph"]["nodes"][1]["name"], "run")

    def test_analyze_returns_empty_report_for_empty_directory(self) -> None:
        with TemporaryDirectory() as directory:
            result = self.run_cli(["analyze", directory])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout)["files"], [])

    def test_analyze_reports_invalid_directory_on_stderr(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            file_path = root / "module.py"
            file_path.touch()

            for target in (root / "missing", file_path):
                with self.subTest(target=target.name):
                    result = self.run_cli(["analyze", str(target)])

                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("目录分析失败：", result.stderr)
                    self.assertIn(target.name, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
