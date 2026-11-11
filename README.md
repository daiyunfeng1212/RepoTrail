# RepoTrail · 代码路标

帮助新人理解陌生仓库：系统由哪些模块组成、各模块做什么、从哪里开始读，以及某个输入经过哪些功能。

项目目标是支持多种语言。当前退回到最小可运行脚手架，按一个功能一轮的方式学习和实现。

## 当前能力

只有命令行启动、帮助和版本显示。仓库扫描、代码解析、关系分析、JSON 存储、图形展示、AI 总结和运行追踪均未实现。

本轮不引入 Tree-sitter，也不保留原先的 Python AST 分析器。以后实现解析功能时再引入对应依赖并说明理由。

## 运行和验证

需要 Python 3.10 或更新版本。当前没有第三方运行时依赖，也不需要先 build 或安装项目。

在项目根目录运行：

```bash
python3 run.py
python3 run.py --help
python3 run.py --version
```

前两条展示帮助，版本命令输出 `repotrail 0.1.0`。当前没有 `analyze`、`serve` 等子命令，旧命令会提示参数不受支持。

虚拟环境是后续安装依赖时使用的独立环境，目前通过系统 Python 即可启动。

可选的开发安装方式：

```bash
python3 -m pip install -e .
repotrail --help
```

安装可能需要下载构建工具；它与通过 `run.py` 直接运行是两种入口方式。

## 目录与阅读顺序

```text
RepoTrail/
├── pyproject.toml           项目信息、打包配置、安装后的命令入口
├── run.py                   从源码目录直接启动
├── src/repotrail/
│   ├── __init__.py          包信息与版本号
│   ├── __main__.py          python -m repotrail 的启动入口
│   └── cli.py               处理命令行参数
├── tests/README.md          后续功能测试的存放约定
├── examples/README.md       后续示例代码的存放约定
└── docs/architecture.md     当前启动链路与后续迭代顺序
```

推荐先读 `run.py` → `cli.py` → `__init__.py`，最后看 `pyproject.toml`。

启动链路：

```text
python3 run.py
  → 将 src 加入 Python 的模块查找路径
  → 导入 repotrail.cli.main
  → argparse 处理参数并显示帮助或版本
  → 返回退出码
```

`run.py` 让项目无需安装即可运行；安装后的 `repotrail` 命令由 `pyproject.toml` 直接指向同一个 `main()`。安装项目或设置 `PYTHONPATH=src` 后也可使用 `python3 -m repotrail`。

## 逐步实现计划

每次只完成其中一个可独立验证的小步骤，完成后先讲解，再由开发者决定下一步：

1. 扫描指定目录，列出文件并过滤 `.git`、`.venv` 等目录。
2. 按扩展名识别候选语言，说明不能识别的文件。
3. 接入 Tree-sitter，先验证一个 Python 文件能生成语法树。
4. 提取单文件函数名称和源码位置。
5. 接入第二种语言，验证不同语言的提取结果如何统一。
6. 把已提取的信息保存为 JSON。
7. 实现一种明确的关系分析，再扩展为仓库级图。
8. 展示图并关联源码；后续另行设计阅读路线与运行追踪。

这是一份计划，不是已实现能力；遇到复杂任务时继续拆成更小的轮次。

## 旧实现备份

精简前的源码、测试、订单示例和相关说明已保存到本地 `docs/tmp/before-scaffold-reset-*.zip`。该目录按现有 `.gitignore` 忽略，不会自动随 Git 提交；需要跨设备保留时请单独保存备份。

旧实现中的 AST 解析、Mermaid 导出和 HTTP API 已从当前代码中移出，对应的旧功能测试也一起归档。当前脚手架采用命令行启动验证，没有宣称旧测试仍然通过。

## 当前可准确描述的成果

“完成了 Python 项目的最小命令行脚手架，统一源码运行和安装后的命令入口，明确了多语言仓库导读的分步开发路线。代码解析与可视化尚未实现。”
