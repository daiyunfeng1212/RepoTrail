"""Versioned graph format shared by analysis, exports, and the future viewer."""
from dataclasses import asdict, dataclass, field


@dataclass
class Node:
    id: str
    kind: str
    name: str
    file: str
    line: int
    end_line: int
    summary: str = ""


@dataclass
class Edge:
    source: str
    target: str
    kind: str
    file: str
    line: int
    evidence: str = "static"


@dataclass
class Graph:
    root: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return asdict(self)
