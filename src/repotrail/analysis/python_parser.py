"""提取 Python 定义、嵌套归属和源码位置。"""

from dataclasses import dataclass
from typing import Literal

import tree_sitter_python
from tree_sitter import Language, Node, Parser


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


def extract_python_symbols(source: str) -> list[Symbol]:
    """按源码提取类、函数、方法及嵌套定义。

    仅分析传入的源码文本，不读取文件或执行代码。
    定义范围从class、def或async def所在行开始，不包含装饰器。
    Tree-sitter 检测到解析错误时抛出SyntaxError,不返回部分结果。
    """
    language = Language(tree_sitter_python.language())

    parser = Parser(language)

    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)

    # 检查错误标记
    if tree.root_node.has_error:
        raise SyntaxError("Tree-sitter 检测到Python源码解析错误")

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

            # 先截取 bytes,再解码，才能正确处理中文等多字节字符
            name = source_bytes[name_node.start_byte : name_node.end_byte].decode(
                "utf-8"
            )

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
