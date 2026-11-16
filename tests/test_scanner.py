"""验证文件扫描的正常行为与重要边界"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from repotrail.scanner import scan_files


class ScanFilesTests(unittest.TestCase):
    def test_returns_sorted_relative_paths(self) -> None:
        # TemporyDirectory 创建临时目录。
        # 退出 with 后自动清理，测试不依赖真实项目中的文件
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()

            # 创建文件并写入文本
            (root / "src" / "b.py").write_text("", encoding="utf-8")
            (root / "z.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")

            # assertEqual 同时验证文件范围、相对路径和排列顺序
            self.assertEqual(
                scan_files(root), [Path("a.py"), Path("src/b.py"), Path("z.py")]
            )

    def test_skips_ignored_directories(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            for name in (".git", ".venv", "__pycache__"):
                ignored = root / name
                ignored.mkdir()
                (ignored / "hidden.py").write_text("", encoding="utf-8")

            # parents=True 会同时创建缺失的父目录 src。
            # 验证嵌套位置的忽略目录也会被跳过。
            nested = root / "src" / ".venv"
            nested.mkdir(parents=True)
            (nested / "hidden.py").write_text("", encoding="utf-8")

            (root / "keep.py").write_text("", encoding="utf-8")

            self.assertEqual(scan_files(root), [Path("keep.py")])

    def test_skips_symbolic_links(self) -> None:
        with TemporaryDirectory() as directory:
            base = Path(directory)

            # repo 是扫描范围，outside 位于扫描范围之外。
            root = base / "repo"
            root.mkdir()

            outside = base / "outside"
            outside.mkdir()

            target = outside / "secret.py"
            target.write_text("", encoding="utf-8")
            (root / "keep.py").write_text("", encoding="utf-8")

            # symlink_to() 在当前路径创建指向目标的符号链接。
            # 当前 Linux 环境支持创建这些链接。
            (root / "linked.py").symlink_to(target)
            (root / "linked-dir").symlink_to(
                outside,
                target_is_directory=True,
            )

            # 指向不存在目标的链接也应跳过。
            (root / "broken.py").symlink_to(base / "missing.py")

            self.assertEqual(scan_files(root), [Path("keep.py")])

    def test_empty_directory_returns_empty_list(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertEqual(scan_files(Path(directory)), [])

    def test_missing_path_raises(self) -> None:
        with TemporaryDirectory() as directory:
            # assertRaises 检查代码是否抛出指定类型的异常。
            # 没抛异常或抛出其他类型，都会使测试失败。
            with self.assertRaises(FileNotFoundError):
                scan_files(Path(directory) / "missing")

    def test_file_as_root_raises(self) -> None:
        with TemporaryDirectory() as directory:
            file = Path(directory) / "single.py"
            file.write_text("", encoding="utf-8")

            with self.assertRaises(NotADirectoryError):
                scan_files(file)

    def test_directory_read_error_propagates(self) -> None:
        with TemporaryDirectory() as directory:
            # patch.object 暂时替换 Path.iterdir 的行为。
            # side_effect 指定调用这个方法时抛出的异常。
            #
            # 这样不需要修改真实目录权限，测试也不会受当前用户
            # 是否拥有管理员权限的影响。
            # 离开 with 后，会自动恢复原方法。
            with patch.object(
                Path,
                "iterdir",
                side_effect=PermissionError("无法读取目录"),
            ):
                with self.assertRaises(PermissionError):
                    scan_files(Path(directory))
