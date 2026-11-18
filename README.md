# RepoTrail · 代码路标

帮助开发者理解陌生仓库：先认识主要模块，再逐层定位文件、类和函数；通过自然语言问题查找相关代码，获得有源码依据的解释与修改位置建议。

首版范围与验收标准已于 2026-11-15 确认，以 [需求分析](docs/requirements.md) 为准；其中列出的能力仍是待实现目标。

## 目前可用

- `scan <目录>` 扫描候选文件，可显示按扩展名推断的语言。
- `parse <文件>` 使用 Tree-sitter 提取 Python 类、函数、嵌套归属和行号。
- `graph <文件>` 输出单文件包含图。Python API `get_children()` 支持逐层查询直接子节点。
- `analyze <目录>` 输出逐文件的分析状态和已成功解析的 Python 文件图谱。
- `imports <文件>` 输出 Python 源码中的静态导入声明及行号。
- 跨文件依赖与调用关系分析、模型接入和浏览器图谱展示仍待实现。

## 安装与运行

需要 Python 3.12 或更高版本。在项目根目录创建并激活虚拟环境后安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

以可编辑模式安装后，可以直接运行：

```bash
repotrail --help
repotrail scan src/repotrail
repotrail scan src/repotrail --show-language
repotrail parse src/repotrail/analysis/python_parser.py
repotrail parse src/repotrail/analysis/python_parser.py --qualified-names
repotrail parse src/repotrail/analysis/python_parser.py --format json
repotrail graph src/repotrail/analysis/python_parser.py
repotrail analyze src/repotrail/analysis
repotrail imports src/repotrail/analysis/repository.py
```

`--show-language` 用制表符分隔候选语言与相对路径，保持按路径排序；
未识别文件显示为 `unknown`，仍保留在清单和总数中。
候选语言仅根据扩展名推断，不代表已经支持对应语言的结构解析。
不带该参数时，继续只显示路径和文件总数。

`parse` 当前接受扩展名为 `.py` 的文件，以只读方式读取源码并提取定义，不执行目标代码。
每行用制表符分隔 `类型`、`名称`、`起始行:结束行`；两个行号均从 1 开始，包含结束行，定义范围不包含装饰器。
没有定义时显示 `共0个定义。` 并成功退出；读取、编码或解析失败时向标准错误输出提示并返回退出码 `1`，参数错误返回 `2`。
解析错误以 Tree-sitter 的错误标记为依据，尚未分析名称绑定或运行正确性。

`--qualified-names` 将名称列切换为包含外层类、函数的限定名，例如 `Service.run`；不带开关时仍显示 `run`。
模块级定义的 `scope` 为空、`parent_name` 为 `None`；内部定义记录外层名称，控制流节点不会增加定义归属层级。
限定名只表达嵌套归属，同一作用域内重复定义仍可能同名，因此不能直接作为唯一节点 ID。

`parse --format json` 输出文件路径、语言及定义列表；`graph` 输出节点和包含边。
成功时 JSON 输出不附加文本统计，失败时错误写入标准错误。
图谱节点 ID 用于本次分析结果，不承诺跨源码修改保持稳定。

`analyze` 把 JSON 报告写到标准输出。`root` 是分析目录的绝对路径，`files` 按相对路径排序，每条记录含路径、候选语言、状态、图谱和说明。空目录的 `files` 是空列表。

退出码 `0` 表示已生成报告。查看文件的 `status` 可区分成功解析（`parsed`）、暂不支持（`unsupported`）和单文件失败（`failed`）。整个目录无法扫描时，仅向标准错误输出原因并返回 `1`。参数用法错误返回 `2`。

`imports` 从 `.py` 文件读取静态导入声明，输出含绝对路径 `file`、`language` 和 `imports` 列表的 JSON。逗号分隔的导入项各占一条记录，按源码顺序排列。每条记录的字段约定如下。

| 字段 | 含义 |
| --- | --- |
| `module` | 声明中的模块名。`from . import name` 没有显式模块名，值为 `null`。 |
| `name` | `from` 语句要导入的名称。通配符用 `"*"`，直接导入模块时为 `null`。 |
| `alias` | `as` 声明的别名，无别名时为 `null`。 |
| `level` | 相对导入的前导点号数量，绝对导入为 `0`。 |
| `line` | 导入语句起始行，从 `1` 开始。 |

提取范围包括函数与条件块中的导入声明。模块定位、动态导入与运行时可达性属于后续分析。无静态导入时成功输出空列表。读取、编码或语法树解析失败时向标准错误输出原因，标准输出为空，退出码为 `1`。参数用法错误返回 `2`。

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

## 技术路线

- 核心与命令行：Python，优先使用标准库。
- 代码解析：按需引入 Tree-sitter，逐种验证待分析语言。
- Agent：模型 SDK 与自行实现的工具调用循环。
- 存储：原型先保存 JSON，出现局部更新和任务管理需求后评估 SQLite。
- 测试：优先使用标准库 `unittest`。
- 后端与界面：需要浏览器交互时再评估 FastAPI，以及 React + TypeScript 前端。

## 后续迭代顺序

1. 扩展 Python 信息提取与文件间关系分析。
2. 设计最小节点、关系结构，保存并查询已提取的信息。
3. 逐步实现模块概览、分层浏览与按需分析。
4. 接入模型 API、工具调用及有源码依据的问答，并评测效果。

语言选择不限制待分析代码的语言范围；多语言解析需要逐种实现和验证。静态关系与实际运行轨迹分别设计。

源码组织见 [架构说明](docs/architecture.md)，测试范围见 [测试说明](tests/README.md)。
