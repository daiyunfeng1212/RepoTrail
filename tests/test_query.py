"""验证单文件图谱的直接子节点查询。"""

import unittest
from copy import deepcopy
from pathlib import Path

from repotrail.analysis.graph import build_file_graph
from repotrail.analysis.python_parser import extract_python_symbols
from repotrail.analysis.query import get_children


class GetChildrenTests(unittest.TestCase):
    def test_queries_one_level_at_a_time(self) -> None:
        source = (
            "class Service:\n"
            "    def first(self):\n"
            "        def helper(): pass\n"
            "    def second(self): pass\n"
            "def top(): pass\n"
        )
        graph = build_file_graph(Path("sample.py"), extract_python_symbols(source))
        file, service, first, helper, second, top = graph["nodes"]

        self.assertEqual(get_children(graph, file["id"]), [service, top])
        self.assertEqual(get_children(graph, service["id"]), [first, second])
        self.assertEqual(get_children(graph, first["id"]), [helper])

    def test_follows_edge_order_without_modifying_graph(self) -> None:
        source = "def first(): pass\ndef second(): pass\n"
        graph = build_file_graph(Path("sample.py"), extract_python_symbols(source))
        file, first, second = graph["nodes"]
        # 调整边的顺序，用来区分按边返回和按节点列表返回。
        graph["edges"].reverse()
        original_graph = deepcopy(graph)

        self.assertEqual(get_children(graph, file["id"]), [second, first])
        self.assertEqual(graph, original_graph)

    def test_returns_empty_list_for_a_leaf(self) -> None:
        graph = build_file_graph(Path("empty.py"), [])
        file = graph["nodes"][0]

        self.assertEqual(get_children(graph, file["id"]), [])

    def test_raises_key_error_with_unknown_node_id(self) -> None:
        graph = build_file_graph(Path("empty.py"), [])

        with self.assertRaises(KeyError) as raised:
            get_children(graph, "missing-node")

        self.assertEqual(raised.exception.args, ("missing-node",))

    def test_distinguishes_repeated_definitions_by_id(self) -> None:
        source = (
            "class Service:\n"
            "    def run(self): pass\n"
            "class Service:\n"
            "    def run(self): pass\n"
        )
        graph = build_file_graph(Path("sample.py"), extract_python_symbols(source))
        _, first_service, first_run, second_service, second_run = graph["nodes"]

        self.assertEqual(get_children(graph, first_service["id"]), [first_run])
        self.assertEqual(get_children(graph, second_service["id"]), [second_run])
