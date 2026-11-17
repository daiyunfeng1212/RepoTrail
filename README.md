# RepoTrail · 代码路标

帮助开发者理解陌生仓库：先认识主要模块，再逐层定位文件、类和函数；通过自然语言问题查找相关代码，获得有源码依据的解释与修改位置建议。

首版范围与验收标准已于 2026-11-15 确认，以 [需求分析](docs/requirements.md) 为准；其中列出的能力仍是待实现目标。

## 当前状态

- 已实现 Python 命令行入口、目录扫描与基础过滤。
- 支持按扩展名识别候选语言，并通过 `--show-language` 展示。
- 已添加扫描、语言识别和命令行集成测试。
- 已接入 Tree-sitter，支持提取 Python 类与函数定义，包括方法、异步和嵌套函数，返回名称、类型和源码行号。
- 支持通过 `parse <文件>` 分析单个 Python 文件，遵循源码编码声明读取内容。
- 提取结果包含定义归属，可通过 `--qualified-names` 展示类、函数的限定名。
- 导入与关系分析、图谱、模型接入和浏览器界面仍待实现。

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
repotrail parse src/repotrail/python_parser.py
repotrail parse src/repotrail/python_parser.py --qualified-names
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

Tree-sitter 与 Python 语法包已引入；其他能力按需推进。默认由开发者手写核心代码，教程提供完整示例、讲解、验证方式和 Git 提交参考。

## 历史备份

切换路线前已将最新 Python 代码、测试及相关文档备份至 `docs/tmp/python-before-typescript-2026-11-13-d32d3bb4.zip`，后续可从中选择恢复最小入口或参考已验证的行为。

该备份目录被 Git 忽略，只保存在本地；此前的历史备份也继续保留。备份不包含可重新创建的虚拟环境。

## 后续迭代顺序

以下均为规划，每轮只完成一个可独立验证的小步骤：

1. 扩展 Python 信息提取与文件间关系分析。
2. 设计最小节点、关系结构，保存并查询已提取的信息。
3. 逐步实现模块概览、分层浏览与按需分析。
4. 接入模型 API、工具调用及有源码依据的问答，并评测效果。

语言选择不限制待分析代码的语言范围；多语言解析需要逐种实现和验证。静态关系与实际运行轨迹分别设计。

## 保留资料

- `AGENTS.md`：开发和教学协作约定。
- `docs/requirements.md`：已确认的首版需求与验收标准，纳入版本管理。
- `docs/idea.md`：产品构想笔记。
- `docs/architecture.md`：当前状态和后续模块边界。
- `examples/order_flow.py`：未来解析器的 Python 输入样例，说明见 `examples/README.md`。
- `tests/README.md`：测试目录当前状态及后续约定。

部分本地资料按现有 `.gitignore` 配置忽略，不会自动进入 Git 提交。
