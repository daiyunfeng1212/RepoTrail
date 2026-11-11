"""Read-only, localhost-bound development API for one explicitly selected repo."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from .analyzer import analyze
from .exporters import to_mermaid


def create_server(repository: str | Path, port: int = 8765) -> ThreadingHTTPServer:
    graph = analyze(repository)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # No CORS: the future viewer and API are served from the same origin.
            host = urlparse('http://' + self.headers.get('Host', '')).hostname
            if host not in {'127.0.0.1', 'localhost'}:
                self.send_error(403)
                return
            path = urlparse(self.path).path
            if path == '/api/health':
                body, content_type = json.dumps({'status': 'ok', 'version': '0.1.0'}), 'application/json'
            elif path == '/api/graph':
                body, content_type = json.dumps(graph.to_dict(), ensure_ascii=False), 'application/json'
            elif path in {'/api/diagram/modules', '/api/diagram/calls'}:
                body, content_type = to_mermaid(graph, path.rsplit('/', 1)[1]), 'text/plain'
            elif path == '/':
                body = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>RepoTrail 开发入口</title><main><h1>RepoTrail</h1>'
                        '<p>脚手架已启动。交互式仓库地图尚未实现；当前可读取分析数据与 Mermaid 图。</p>'
                        '<ul><li><a href="/api/graph">仓库图 JSON</a></li>'
                        '<li><a href="/api/diagram/modules">模块依赖图（Mermaid 源码）</a></li>'
                        '<li><a href="/api/diagram/calls">函数调用图（Mermaid 源码）</a></li>'
                        '</ul><p>分析结果为启动时快照，更新源码后请重启服务。</p></main></html>')
                content_type = 'text/html'
            else:
                self.send_error(404)
                return
            encoded = body.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(encoded)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def serve_repository(repository: str | Path, port: int = 8765):
    server = create_server(repository, port)
    print(f'RepoTrail 开发 API: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
