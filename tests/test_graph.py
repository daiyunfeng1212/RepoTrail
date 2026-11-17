"""验证单文件图谱的节点标识和包含关系。"""

import unittest
from pathlib import Path

from repotrail.graph import build_file_graph
from repotrail.python_parser import extract_python_symbols


class BuildFileGraphTests(unittest.TestCase):
    def test_builds_nested_and_sibling_containment(self) -> None:
        source = (
            "class Service:\n"
            "    def first(self):\n"
            "        def helper(): pass\n"
            "    def second(self): pass\n"
            "def top(): pass\n"
        )

        graph = build_file_graph(
            Path("sample.py"),
            extract_python_symbols(source),
        )
        nodes = graph["nodes"]
        edges = graph["edges"]

        # 验证节点顺序、类型、限定名和源码位置被正确保留。
        self.assertEqual(
            [
                (
                    node["kind"],
                    node["qualified_name"],
                    node["start_line"],
                    node["end_line"],
                )
                for node in nodes
            ],
            [
                ("file", None, None, None),
                ("class", "Service", 1, 4),
                ("function", "Service.first", 2, 3),
                ("function", "Service.first.helper", 3, 3),
                ("function", "Service.second", 4, 4),
                ("function", "top", 5, 5),
            ],
        )

        # 节点下标：
        # 0 文件，1 Service，2 first，3 helper，4 second，5 top。
        #
        # helper 属于 first，second 返回类层级，top 返回文件层级。
        # 使用结果中的 ID 验证关系，不依赖 ID 的具体字符串格式。
        self.assertEqual(
            edges,
            [
                {
                    "source": nodes[parent]["id"],
                    "target": nodes[child]["id"],
                    "kind": "contains",
                }
                for parent, child in (
                    (0, 1),
                    (1, 2),
                    (2, 3),
                    (1, 4),
                    (0, 5),
                )
            ],
        )

    def test_repeated_names_keep_distinct_nodes_and_parents(self) -> None:
        source = (
            "class Service:\n"
            "    def run(self): pass\n"
            "class Service:\n"
            "    def run(self): pass\n"
        )

        graph = build_file_graph(
            Path("sample.py"),
            extract_python_symbols(source),
        )
        nodes = graph["nodes"]

        # 文件节点，加上两个类和两个方法。
        self.assertEqual(len(nodes), 5)

        # 集合会去重，数量相同意味着没有重复节点 ID。
        self.assertEqual(
            len({node["id"] for node in nodes}),
            len(nodes),
        )

        # 两个方法的限定名相同，但节点和父节点必须区分。
        self.assertEqual(
            nodes[2]["qualified_name"],
            nodes[4]["qualified_name"],
        )
        self.assertEqual(
            graph["edges"][1]["source"],
            nodes[1]["id"],
        )
        self.assertEqual(
            graph["edges"][3]["source"],
            nodes[3]["id"],
        )

    def test_empty_definitions_keep_file_node(self) -> None:
        path = Path("empty.py")
        graph = build_file_graph(path, [])

        self.assertEqual(len(graph["nodes"]), 1)

        node = graph["nodes"][0]
        self.assertEqual(node["kind"], "file")
        self.assertEqual(node["name"], "empty.py")
        self.assertEqual(
            node["file"],
            path.absolute().as_posix(),
        )
        self.assertEqual(graph["edges"], [])