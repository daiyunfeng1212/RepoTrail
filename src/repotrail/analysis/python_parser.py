"""提取 Python 定义、导入声明和源码位置。"""

from dataclasses import dataclass
from typing import Literal, TypedDict

import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree


@dataclass
class Symbol:
    """单个定义的名称、类型与源码范围。

    行号从1开始，包含结束行。
    scope 保存由外到内的所属类、函数名称；模块级定义为空元组。
    限定名用于展示归属，不保证在同一文件中唯一。
    """

    name: str
    kind: Literal["class", "function"]
    start_line: int
    end_line: int
    scope: tuple[str, ...] = ()

    @property
    def qualified_name(self) -> str:
        """根据外层名称计算限定名，如 Service.run.helper。"""
        # 展开外层名称，再加入当前名称，用点号连接成展示文本。
        return ".".join((*self.scope, self.name))

    @property
    def parent_name(self) -> str | None:
        """返回直接所属定义的限定名；模块级定义返回 None。"""
        return ".".join(self.scope) if self.scope else None


class PythonImport(TypedDict):
    """一个导入项及其语句起始行。level 表示相对导入的前导点号数量。"""

    module: str | None
    name: str | None
    alias: str | None
    level: int
    line: int


def _parse_python(source_bytes: bytes) -> Tree:
    """解析 UTF-8 源码。遇到语法树错误时拒绝输出部分结果。"""
    parser = Parser(Language(tree_sitter_python.language()))
    tree = parser.parse(source_bytes)
    if tree.root_node.has_error:
        raise SyntaxError("Tree-sitter 检测到Python源码解析错误")
    return tree


def _node_text(node: Node, source_bytes: bytes) -> str:
    # Tree-sitter 的偏移量以字节计数，按字节截取可保留 Unicode 名称。
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


def _dotted_name(node: Node, source_bytes: bytes) -> str:
    # 按标识符拼接，避免把点号周围的空格或续行符算进模块名。
    return ".".join(
        _node_text(child, source_bytes)
        for child in node.named_children
        if child.type == "identifier"
    )


def extract_python_symbols(source: str) -> list[Symbol]:
    """按源码提取类、函数、方法及嵌套定义。

    仅分析传入的源码文本，不读取文件或执行代码。
    定义范围从class、def或async def所在行开始，不包含装饰器。
    Tree-sitter 检测到解析错误时抛出SyntaxError,不返回部分结果。
    """
    source_bytes = source.encode("utf-8")
    tree = _parse_python(source_bytes)

    symbols: list[Symbol] = []
    # 每个待处理项同时保存节点及它所处的定义作用域。
    pending: list[tuple[Node, tuple[str, ...]]] = [(tree.root_node, ())]

    while pending:
        node, scope = pending.pop()
        # 普通语法节点沿用作用域，定义节点再为其内部增加一层归属。
        child_scope = scope

        if node.type in ("class_definition", "function_definition"):
            name_node = node.child_by_field_name("name")

            if name_node is None:
                raise RuntimeError("Tree-sitter 定义节点缺少name字段")

            name = _node_text(name_node, source_bytes)

            # end_point 表示不包含在节点中的结束位置
            end_line = node.end_point.row + 1
            if node.end_point.column == 0:
                end_line -= 1

            symbols.append(
                Symbol(
                    name=name,
                    kind=("class" if node.type == "class_definition" else "function"),
                    start_line=node.start_point.row + 1,
                    end_line=end_line,
                    scope=scope,
                )
            )

            # 新元组不会修改同级其他定义的作用域。
            child_scope = (*scope, name)

        # 倒序入栈保持源码顺序；if、for 等普通节点不增加归属层级。
        pending.extend((child, child_scope) for child in reversed(node.named_children))

    return symbols


def extract_python_imports(source: str) -> list[PythonImport]:
    """按源码顺序提取静态导入，每个模块或名称对应一条记录。

    `import` 的 name 为空，`from . import` 的 module 为空。函数体和条件块
    内的导入同样记录。分析仅使用语法树，解析错误时抛出 SyntaxError。
    """
    source_bytes = source.encode("utf-8")
    tree = _parse_python(source_bytes)
    imports: list[PythonImport] = []
    pending = [tree.root_node]

    while pending:
        node = pending.pop()
        if node.type not in (
            "import_statement",
            "import_from_statement",
            "future_import_statement",
        ):
            pending.extend(reversed(node.named_children))
            continue

        direct = node.type == "import_statement"
        level = 0
        module = "__future__" if node.type == "future_import_statement" else None
        module_node = node.child_by_field_name("module_name")
        if module_node is not None:
            if module_node.type == "relative_import":
                for child in module_node.named_children:
                    if child.type == "import_prefix":
                        level = sum(token.type == "." for token in child.children)
                    elif child.type == "dotted_name":
                        module = _dotted_name(child, source_bytes)
            else:
                module = _dotted_name(module_node, source_bytes)

        targets = node.children_by_field_name("name")
        # 语法树给普通导入项标注 name 字段，通配符单独使用节点类型。
        targets.extend(
            child for child in node.named_children if child.type == "wildcard_import"
        )
        for target in targets:
            alias = None
            if target.type == "aliased_import":
                alias_node = target.child_by_field_name("alias")
                name_node = target.child_by_field_name("name")
                if alias_node is None or name_node is None:
                    raise RuntimeError("Tree-sitter 导入别名缺少名称或别名字段")
                alias = _node_text(alias_node, source_bytes)
                target = name_node

            imported = (
                "*" if target.type == "wildcard_import" else _dotted_name(target, source_bytes)
            )
            imports.append(
                PythonImport(
                    module=imported if direct else module,
                    name=None if direct else imported,
                    alias=alias,
                    level=level,
                    line=node.start_point.row + 1,
                )
            )

    return imports
