"""把单个 Python 文件的定义列表转换为包含关系图。"""

from pathlib import Path
from typing import Literal, TypedDict

from repotrail.python_parser import Symbol


class GraphNode(TypedDict):
    """文件或定义节点。

    文件节点不记录定义的限定名和行号范围，对应字段为 None。
    """

    id: str
    kind: Literal["file", "class", "function"]
    name: str
    file: str
    qualified_name: str | None
    start_line: int | None
    end_line: int | None


class GraphEdge(TypedDict):
    """有方向的包含边：source 包含 target。"""

    source: str
    target: str
    kind: Literal["contains"]


class FileGraph(TypedDict):
    """单文件图谱，包含节点列表和边列表。"""

    nodes: list[GraphNode]
    edges: list[GraphEdge]


def build_file_graph(path: Path, symbols: list[Symbol]) -> FileGraph:
    """从同一源码的提取结果生成图谱，不读取或执行文件。

    symbols 必须保持 extract_python_symbols 返回的源码遍历顺序和作用域。
    ID 保证本次生成中不同节点可区分，不承诺跨源码修改保持稳定。
    """
    file_path = path.absolute().as_posix()
    file_id = f"file:{file_path}"

    # 即使文件中没有类和函数，也应保留文件本身。
    nodes: list[GraphNode] = [
        {
            "id": file_id,
            "kind": "file",
            "name": path.name,
            "file": file_path,
            "qualified_name": None,
            "start_line": None,
            "end_line": None,
        }
    ]

    edges: list[GraphEdge] = []

    # 保存当前嵌套路径上各定义的节点 ID。
    # 文件根节点单独处理，不放入这个栈。
    ancestors: list[str] = []

    for index, symbol in enumerate(symbols):
        # enumerate() 同时提供序号和元素。
        # 序号区分同一文件中的重复定义，限定名只用于展示。
        node_id = f"symbol:{file_path}:{index}"

        # scope 的长度就是定义所处的嵌套深度：
        # 顶层定义为 0，类中的方法为 1，方法中的函数为 2。
        depth = len(symbol.scope)

        # 遇到同级或上层定义时，移除已经离开的内层节点。
        # 深度来自解析器记录的归属，无需通过缩进或名称猜测。
        while len(ancestors) > depth:
            ancestors.pop()

        # 栈顶是直接父定义；没有外层定义时，父节点就是文件。
        parent_id = ancestors[-1] if ancestors else file_id

        nodes.append(
            {
                "id": node_id,
                "kind": symbol.kind,
                "name": symbol.name,
                "file": file_path,
                "qualified_name": symbol.qualified_name,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
            }
        )

        # 每个定义都有一条来自直接父节点的包含边。
        edges.append(
            {
                "source": parent_id,
                "target": node_id,
                "kind": "contains",
            }
        )

        # 当前定义成为后续内部定义的候选父节点。
        ancestors.append(node_id)

    return {"nodes": nodes, "edges": edges}