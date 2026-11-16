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

`test_languages.py` 验证语言扩展名别名、大小写匹配、未知或缺失扩展名，以及无需文件实际存在的分类行为。

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
