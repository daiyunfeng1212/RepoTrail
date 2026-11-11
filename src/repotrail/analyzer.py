"""Conservative AST indexing. Never imports or executes the target repository."""
import ast
import os
from pathlib import Path
import tokenize

from .models import Edge, Graph, Node

EXCLUDED = {".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
            "__pycache__", "build", "dist", ".tox", ".mypy_cache", ".pytest_cache"}
MAX_FILE_BYTES = 2_000_000
MAX_FILES = 5000


def _module_name(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or "__root__"


def _summary(node: ast.AST) -> str:
    text = ast.get_docstring(node) or ""
    return text.strip().splitlines()[0] if text.strip() else ""


def _local_module(name: str, modules: dict) -> str | None:
    while name:
        if name in modules:
            return name
        name = name.rpartition(".")[0]
    return None


class Indexer(ast.NodeVisitor):
    def __init__(self, module: str, file: str, graph: Graph):
        self.module, self.file, self.graph = module, file, graph
        self.scope: list[str] = []
        self.callables: list[tuple[ast.AST, str]] = []
        self.imports: dict[str, str] = {}
        self.import_lines: list[tuple[str, int]] = []
        self.package = module if file.endswith("__init__.py") else module.rpartition(".")[0]

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope.append(node.name)
        self.graph.nodes.append(Node(f"{self.module}:{'.'.join(self.scope)}", "class",
                                     '.'.join(self.scope), self.file, node.lineno,
                                     node.end_lineno or node.lineno, _summary(node)))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope.append(node.name)
        symbol = f"{self.module}:{'.'.join(self.scope)}"
        self.graph.nodes.append(Node(symbol, "async_function" if isinstance(node, ast.AsyncFunctionDef)
                                     else "function", '.'.join(self.scope), self.file,
                                     node.lineno, node.end_lineno or node.lineno, _summary(node)))
        self.callables.append((node, symbol))
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
            self.import_lines.append((alias.name, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level:
            parts = self.package.split('.') if self.package else []
            base = parts[:len(parts) - node.level + 1] if node.level <= len(parts) else []
            prefix = '.'.join(base + ([node.module] if node.module else []))
        else:
            prefix = node.module or ""
        for alias in node.names:
            if alias.name != "*":
                target = '.'.join(filter(None, [prefix, alias.name]))
                self.imports[alias.asname or alias.name] = target
                self.import_lines.append((target, node.lineno))


def _calls_in_body(node: ast.AST):
    """Do not attribute nested callable bodies or decorators to their outer function."""
    for statement in getattr(node, "body", []):
        stack = [statement]
        while stack:
            current = stack.pop()
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(current, ast.Call):
                yield current
            stack.extend(reversed(list(ast.iter_child_nodes(current))))


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def analyze(repository: str | Path) -> Graph:
    root = Path(repository).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"仓库目录不存在：{root}")
    graph = Graph(str(root))
    # Common src layout: names are relative to src/, while file paths remain repo-relative.
    source_root = root / "src" if (root / "src").is_dir() else root
    modules: dict[str, Indexer] = {}
    paths: list[Path] = []
    for directory, dirs, files in os.walk(source_root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith('.'))
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix == '.py' and not path.is_symlink():
                paths.append(path)
                if len(paths) > MAX_FILES:
                    raise ValueError(f"超过 {MAX_FILES} 个 Python 文件，请选择更小的子目录")
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                graph.warnings.append(f"跳过超过 2 MB 的文件：{relative}")
                continue
            with tokenize.open(path) as stream:
                tree = ast.parse(stream.read(), filename=relative)
        except (OSError, SyntaxError, UnicodeError, LookupError) as error:
            graph.warnings.append(f"无法解析 {relative}: {error}")
            continue
        name = _module_name(path.relative_to(source_root))
        graph.nodes.append(Node(name, "module", name, relative, 1,
                                max((getattr(n, 'end_lineno', 1) or 1 for n in ast.walk(tree)), default=1),
                                _summary(tree)))
        indexer = Indexer(name, relative, graph)
        indexer.visit(tree)
        modules[name] = indexer
    symbols = {n.id for n in graph.nodes if n.kind != 'module'}
    unresolved = 0
    for name, indexer in modules.items():
        for imported, line in indexer.import_lines:
            target = _local_module(imported, modules)
            if target and target != name:
                graph.edges.append(Edge(name, target, "imports", indexer.file, line))
        for node, source in indexer.callables:
            for call in _calls_in_body(node):
                dotted = _dotted(call.func)
                if not dotted:
                    unresolved += 1
                    continue
                target = None
                # Resolve lexical names, then explicitly imported project symbols.
                if '.' not in dotted:
                    scope = source.split(':', 1)[1].split('.')
                    while scope:
                        candidate = f"{name}:{'.'.join(scope + [dotted])}"
                        if candidate in symbols:
                            target = candidate
                            break
                        scope.pop()
                    candidate = f"{name}:{dotted}"
                    if target is None and candidate in symbols:
                        target = candidate
                head, *tail = dotted.split('.')
                if target is None and head in indexer.imports:
                    qualified = '.'.join([indexer.imports[head], *tail])
                    for module in sorted(modules, key=len, reverse=True):
                        if qualified.startswith(module + '.'):
                            candidate = f"{module}:{qualified[len(module) + 1:]}"
                            if candidate in symbols:
                                target = candidate
                                break
                if target:
                    graph.edges.append(Edge(source, target, 'calls', indexer.file, call.lineno))
                else:
                    unresolved += 1
    if unresolved:
        graph.warnings.append(f"{unresolved} 处调用未连接到仓库内符号（可能是内置函数、外部依赖或动态调用）。")
    graph.warnings.append("静态调用边是候选关系，可能受名称覆盖、条件分支或导入方式影响；不代表实际执行路径。")
    return graph
