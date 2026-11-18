"""查询单文件图谱中的包含关系。"""

from repotrail.analysis.graph import FileGraph, GraphNode


def get_children(graph: FileGraph, node_id: str) -> list[GraphNode]:
    """按包含边的顺序返回指定节点的直接子节点。

    graph 由 build_file_graph() 生成，node_id 为本次图谱中的节点 ID。
    叶节点返回空列表。节点 ID 不存在时抛出 KeyError(node_id)。
    """
    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    if node_id not in nodes_by_id:
        raise KeyError(node_id)

    return [
        nodes_by_id[edge["target"]]
        for edge in graph["edges"]
        if edge["source"] == node_id and edge["kind"] == "contains"
    ]
