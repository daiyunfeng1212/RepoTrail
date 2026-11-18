# RepoTrail 架构

首版范围见 [需求分析](requirements.md)，已实现命令与用法见 [README](../README.md)。

## 当前目录与依赖

- `src/repotrail/__init__.py`：项目版本。
- `src/repotrail/__main__.py`：模块启动入口，调用 `cli.main()`。
- `src/repotrail/cli.py`：参数处理、输入读取、结果与错误展示。
- `src/repotrail/analysis/scanner.py`：文件收集与基础过滤。
- `src/repotrail/analysis/languages.py`：按扩展名识别候选语言。
- `src/repotrail/analysis/python_parser.py`：使用同一套语法树解析逻辑提取定义、嵌套归属、导入声明和行号。
- `src/repotrail/analysis/import_resolution.py`：从已扫描的文件清单静态定位 Python 相对导入。
- `src/repotrail/analysis/graph.py`：从定义结果构建单文件包含图。
- `src/repotrail/analysis/query.py`：按节点 ID 查询单文件图谱的直接子节点。叶节点返回空列表，未知 ID 抛出 `KeyError`。
- `src/repotrail/analysis/repository.py`：组合扫描、分类、提取与图谱构建，记录每个文件的分析状态。

依赖由命令行或目录编排指向具体分析模块；图谱构建依赖解析结果类型，底层模块不反向依赖命令行。
`analysis/__init__.py` 只说明包职责，不引入额外转发接口或初始化副作用。
测试保留在根目录 `tests/`，导入与模拟目标统一使用 `repotrail.analysis.*`。

`resolve_relative_import(source_file, declaration, indexed_files)` 接收 `extract_python_imports()` 生成的记录。源文件和清单路径均相对于调用方选定的 Python 导入根目录。例如 `src` 布局可将 `src` 作为根目录，源文件传 `pkg/main.py`。函数返回清单中的 `.py` 文件路径或包的 `__init__.py`，找不到对应文件、超出包层级或遇到绝对导入时返回 `None`。对于 `from . import name`，只定位包的 `__init__.py`，`name` 的绑定由后续分析处理。

## 规划中的职责边界

- 关系分析：结合导入、作用域等证据解析关系，保留无法确定的情况。
- 存储与导出：保存分析结果和状态，提供明确的数据接口。
- 展示：消费图数据，支持模块概览与分层浏览。
- Agent：调用检索和源码读取工具，组织有证据的解释，并控制执行范围与成本。

这些模块按实际需求逐步实现，当前不预先建立注册器、复杂框架或完整图谱模型。运行追踪将来独立设计；静态调用关系不能当作实际执行顺序。

## 输入样例

`examples/order_flow.py` 是供未来解析器分析的输入，不是 RepoTrail 的实现代码。保留它及手工预期关系，便于后续验证多语言解析。
