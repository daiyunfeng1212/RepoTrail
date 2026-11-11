"""Small, dependency-free exporters; graph data stays independent of the viewer."""
import json

from .models import Graph


def to_json(graph: Graph) -> str:
    return json.dumps(graph.to_dict(), ensure_ascii=False, indent=2) + '\n'


def to_mermaid(graph: Graph, view: str = 'modules', entry: str | None = None) -> str:
    if view not in {'modules', 'calls'}:
        raise ValueError('view must be modules or calls')
    kind = 'imports' if view == 'modules' else 'calls'
    nodes = [n for n in graph.nodes if (n.kind == 'module') == (view == 'modules')]
    edges = [e for e in graph.edges if e.kind == kind]
    if entry:
        if not any(n.id == entry for n in nodes):
            raise ValueError(f'入口不存在于当前视图：{entry}')
        reachable = {entry}
        pending = [entry]
        while pending:
            source = pending.pop()
            for edge in edges:
                if edge.source == source and edge.target not in reachable:
                    reachable.add(edge.target)
                    pending.append(edge.target)
        nodes = [n for n in nodes if n.id in reachable]
        edges = [e for e in edges if e.source in reachable and e.target in reachable]
    identifiers = {n.id: f'n{i}' for i, n in enumerate(nodes)}
    lines = ['flowchart LR', '    %% 静态候选关系，不代表一次实际运行']
    for node in nodes:
        label = f'{node.name} · {node.file}:{node.line}'
        # Mermaid quoted strings use entity codes, not backslash escaping.
        label = label.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        lines.append(f'    {identifiers[node.id]}["{label}"]')
    seen = set()
    for edge in edges:
        pair = (edge.source, edge.target)
        if pair in seen or edge.source not in identifiers or edge.target not in identifiers:
            continue
        seen.add(pair)
        lines.append(f'    {identifiers[edge.source]} --> {identifiers[edge.target]}')
    return '\n'.join(lines) + '\n'
