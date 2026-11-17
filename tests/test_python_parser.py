import unittest

from repotrail.python_parser import Symbol, extract_python_symbols


class ExtractPythonSymbolsTests(unittest.TestCase):
    def test_extracts_nested_and_decorated_definitions(self) -> None:
        # 相邻字符串自动拼接成一段源码。

        source = (
            "class Service:\n"
            "    @staticmethod\n"
            "    def run():\n"
            "        def helper():\n"
            "            return 1\n"
            "        return helper()\n"
            "\n"
            "@cache\n"
            "async def load():\n"
            '    return "ok"\n'
        )

        self.assertEqual(
            extract_python_symbols(source),
            [
                Symbol("Service", "class", 1, 6),
                Symbol("run", "function", 3, 6, scope=("Service",)),
                Symbol("helper", "function", 4, 5, scope=("Service", "run")),
                Symbol("load", "function", 9, 10),
            ],
        )

    def test_handles_utf8_names_and_offsets(self) -> None:
        # 定义前和名称本身都包含中文，验证字节偏移处理正确。
        source = '# 中文注释\n变量 = "中文"\ndef 问候():\n    return "你好"\n'

        self.assertEqual(
            extract_python_symbols(source),
            [Symbol("问候", "function", 3, 4)],
        )

    def test_source_without_definitions_returns_empty_list(self) -> None:
        # 空源码合法；注释和字符串中的 def 也不应被误判。
        for source in (
            "",
            "# def fake(): pass\n",
            'text = "def fake(): pass"\n',
        ):
            with self.subTest(source=source):
                self.assertEqual(extract_python_symbols(source), [])

    def test_parse_errors_raise_instead_of_returning_partial_results(self) -> None:
        for source in (
            "def broken(:\n    pass\n",
            "def valid():\n    pass\n\ndef broken(:\n    pass\n",
        ):
            # 第二个场景前面有完整定义，后面存在解析错误。
            # 整次调用仍应失败，避免误认为已经完整提取。
            #
            # 两个上下文分别标记测试场景、检查异常类型。
            with self.subTest(source=source), self.assertRaises(SyntaxError):
                extract_python_symbols(source)

    def test_distinguishes_same_names_by_owner(self) -> None:
        source = (
            "class User:\n"
            "    def save(self): pass\n"
            "class Order:\n"
            "    def save(self): pass\n"
            "def save(): pass\n"
        )
        symbols = extract_python_symbols(source)

        # 相同简单名称对应不同归属；模块级定义没有父定义。
        self.assertEqual(
            [(s.name, s.qualified_name, s.parent_name) for s in symbols],
            [
                ("User", "User", None),
                ("save", "User.save", "User"),
                ("Order", "Order", None),
                ("save", "Order.save", "Order"),
                ("save", "save", None),
            ],
        )

    def test_control_flow_does_not_add_definition_scope(self) -> None:
        source = (
            "if True:\n"
            "    def outer():\n"
            "        if True:\n"
            "            class Local:\n"
            "                def run(self):\n"
            "                    pass\n"
        )
        symbols = extract_python_symbols(source)

        # if 不增加定义归属，函数中的类、类中的方法则逐层增加。
        self.assertEqual(
            [(s.qualified_name, s.parent_name) for s in symbols],
            [
                ("outer", None),
                ("outer.Local", "outer"),
                ("outer.Local.run", "outer.Local"),
            ],
        )
