import argparse
from pathlib import Path
import sys

from . import __version__
from .analyzer import analyze
from .exporters import to_json, to_mermaid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='RepoTrail · 陌生 Python 仓库的阅读起点')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command', required=True)
    scan = commands.add_parser('analyze', help='静态解析仓库，不执行目标代码')
    scan.add_argument('repository', type=Path)
    scan.add_argument('--format', choices=['json', 'mermaid'], default='json')
    scan.add_argument('--view', choices=['modules', 'calls'], default='modules')
    scan.add_argument('--entry', help='Mermaid 图的起点，例如 main:submit_order')
    scan.add_argument('--output', '-o', type=Path)
    serve = commands.add_parser('serve', help='启动只读本地开发 API')
    serve.add_argument('repository', type=Path)
    serve.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            from .server import serve_repository
            serve_repository(args.repository, args.port)
            return 0
        if args.entry and args.format != 'mermaid':
            parser.error('--entry 目前只适用于 --format mermaid')
        graph = analyze(args.repository)
        output = to_json(graph) if args.format == 'json' else to_mermaid(graph, args.view, args.entry)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding='utf-8')
            print(f'已写入 {args.output.resolve()}', file=sys.stderr)
        else:
            print(output, end='')
        return 0
    except (OSError, ValueError) as error:
        print(f'RepoTrail: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
