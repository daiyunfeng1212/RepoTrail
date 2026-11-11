# 测试目录

后续每轮功能的测试放在这里，优先使用 Python 标准库 `unittest`。

当前只完成命令行脚手架，用项目根目录的以下命令检查启动：

```bash
python3 run.py --help
python3 run.py --version
```

目前没有自动化功能测试，不将 `unittest` 发现零个测试视为功能验证。下一轮实现目录扫描时，再覆盖正常目录、无效路径和目录过滤等关键行为。
