# 测试说明

使用 Python 标准库 unittest 验证功能行为，无需安装额外测试依赖。

## 运行方式

在项目根目录激活虚拟环境，并以可编辑模式安装项目：

```bash
cd /home/lmf/Projects/active/RepoTrail
source .venv/bin/activate
python -m pip install -e .
```

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

只运行文件扫描测试：

```bash
python -m unittest discover -s tests -p "test_scanner.py" -v
```

可编辑安装后，Python 可以找到 `repotrail` 包，无需设置 `PYTHONPATH`。
`-v` 显示每个测试用例的名称和执行结果。

## 模块导入

分析代码统一位于 `src/repotrail/analysis/`，测试通过新包路径导入，例如：

```python
from repotrail.analysis.python_parser import extract_python_symbols
```

模拟文件读取的目标也使用对应模块路径：`repotrail.analysis.repository.tokenize.open`。
测试文件继续保留在当前目录，原有发现命令不变。

## 当前测试范围

`test_scanner.py` 验证 `scan_files()`：

- 收集嵌套目录中的文件，返回排序后的相对路径。
- 跳过指定忽略目录，包括嵌套位置的忽略目录。
- 跳过文件符号链接、目录符号链接和失效链接。
- 空目录返回空列表。
- 路径不存在时抛出 FileNotFoundError。
- 根路径是文件时抛出 NotADirectoryError。
- 读取目录失败时向调用方传播 PermissionError。

`test_cli.py` 通过真实子进程验证命令行帮助、版本、参数错误、扫描结果、空目录和文件系统错误的输出与退出码，
并验证 `--show-language` 展示候选语言、保留未知类型文件及维持路径顺序和总数。
`parse` 的集成场景覆盖定义及行号输出、源码不执行、无定义文件、源码编码声明，以及缺失文件、目录输入、解析错误、解码错误和不支持的文件类型。
同时验证 `--qualified-names` 展示定义归属，默认名称输出仍由原有用例验证。

`test_languages.py` 验证语言扩展名别名、大小写匹配、未知或缺失扩展名，以及无需文件实际存在的分类行为。

`test_python_parser.py` 验证类、方法、嵌套和装饰定义的提取，UTF-8 名称与行号，无定义结果及解析错误时拒绝部分结果。
还验证所属定义与限定名、同名定义的归属区分，以及控制流节点不增加定义归属层级。

`test_graph.py` 验证嵌套与同级定义的包含边、同名定义的独立节点和父节点，以及空定义列表的文件节点。

`test_query.py` 验证直接子节点查询、边顺序、同名节点区分、叶节点和未知 ID。

`test_repository.py` 验证混合文件状态、空目录、无效根目录、编码错误、单文件读取失败后的继续分析，以及扫描过滤规则复用。

命令行测试还覆盖定义 JSON、图谱 JSON、中文输出、空结果和失败时不输出部分结果。

`analyze` 的命令行测试验证混合目录的可读 JSON、空目录报告、无效路径在标准错误输出原因，以及帮助和缺少目录参数的退出码。

`imports` 的命令行测试验证普通导入、别名、相对层级、空结果及无效输入的输出与退出码。解析器测试覆盖多行与嵌套导入、Unicode 名称、通配符和 `__future__`。

## 测试约定

- 文件使用 test_*.py 命名，测试方法使用 test_* 命名。
- 使用 TemporaryDirectory 创建测试数据，测试结束后自动清理。
- 不依赖开发者机器上的固定目录或真实仓库。
- 对正常行为和重要边界编写测试，避免重复验证同一行为。
- 使用 mock 模拟目录读取错误；这不代表已验证所有真实权限场景。

## 平台限制

符号链接用例要求运行环境允许创建符号链接。
Windows 环境可能需要相应权限或系统设置。

当前尚未完成 Windows 平台验证，不能据此宣称已支持全部
Windows 路径及目录联接等特殊情况。

## 结果判定

以实际命令输出为准：

- OK：本次执行的测试通过。
- FAILED 或报错：需要检查失败原因。
- 出现 skipped：有用例未执行，需要关注跳过原因。
- 发现零个测试：不能视为功能验证通过。
