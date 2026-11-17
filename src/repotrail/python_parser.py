"""用Tree-sitter 提取 Python 类与函数定义。"""

from dataclasses import dataclass
from typing import Literal

import tree_sitter_python
from tree_sitter import Language, Parser

@dataclass
class Symbol:
    """单个定义的名称、类型与源码范围。
    
    行号从1开始，包含结束行。
    """
    name: str
    kind: Literal["class","function"]
    start_line: int
    end_line: int

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
    pending = [tree.root_node]

    while pending:
        node = pending.pop()

        if node.type in ("class_definition", "function_definition"):
            name_node = node.child_by_field_name("name")

            if name_node is None:
                raise RuntimeError("Tree-sitter 定义节点缺少name字段")

            # 先截取 bytes,再解码，才能正确处理中文等多字节字符
            name = source_bytes[
                name_node.start_byte:name_node.end_byte
            ].decode("utf-8")

            # end_point 表示不包含在节点中的结束位置
            end_line = node.end_point.row + 1
            if node.end_point.column == 0:
                end_line -= 1

            symbols.append(
                Symbol(
                    name = name,
                    kind=(
                        "class"
                        if node.type == "class_definition"
                        else "function"
                    ),
                    start_line=node.start_point.row + 1,
                    end_line=end_line,
                )
            )

        # 定义内部继续遍历，从而找到方法和嵌套定义
        pending.extend(reversed(node.named_children))

    return symbols


