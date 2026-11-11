import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from repotrail.analyzer import analyze
from repotrail.cli import main
from repotrail.exporters import to_json, to_mermaid


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def test_sample_project_has_source_backed_calls(self):
        sample = Path(__file__).resolve().parents[1] / 'examples' / 'order_demo'
        graph = analyze(sample)
        calls = [e for e in graph.edges if e.kind == 'calls']
        self.assertEqual({e.target for e in calls}, {
            'validation:validate_order', 'pricing:calculate_total', 'storage:save_order'})
        self.assertTrue(all(e.source == 'main:submit_order' for e in calls))
        self.assertTrue(all(e.file == 'main.py' and e.line > 1 for e in calls))
        self.assertEqual(len([n for n in graph.nodes if n.kind == 'module']), 4)

    def test_analysis_never_executes_source(self):
        marker = self.root / 'executed'
        self.write('danger.py', f'from pathlib import Path\nPath({str(marker)!r}).touch()\ndef run(): pass\n')
        graph = analyze(self.root)
        self.assertFalse(marker.exists())
        self.assertIn('danger:run', {n.id for n in graph.nodes})

    def test_relative_alias_import_and_src_layout(self):
        self.write('src/shop/__init__.py', '')
        self.write('src/shop/pricing.py', 'def total(order): return 1\n')
        self.write('src/shop/main.py', 'from .pricing import total as price\nasync def run(order):\n return price(order)\n')
        graph = analyze(self.root)
        self.assertIn(('shop.main:run', 'shop.pricing:total'),
                      {(e.source, e.target) for e in graph.edges if e.kind == 'calls'})
        node = next(n for n in graph.nodes if n.id == 'shop.main:run')
        self.assertEqual(node.kind, 'async_function')
        self.assertEqual(node.file, 'src/shop/main.py')

    def test_nested_calls_are_not_attributed_to_outer_function(self):
        self.write('main.py', 'def leaf(): pass\ndef outer():\n def inner():\n  leaf()\n inner()\n')
        graph = analyze(self.root)
        calls = {(e.source, e.target) for e in graph.edges if e.kind == 'calls'}
        self.assertEqual(calls, {('main:outer', 'main:outer.inner'), ('main:outer.inner', 'main:leaf')})

    def test_broken_file_does_not_hide_valid_modules(self):
        self.write('broken.py', 'def broken(\n')
        self.write('valid.py', '"""Useful module."""\ndef run(): pass\n')
        graph = analyze(self.root)
        self.assertIn('valid:run', {n.id for n in graph.nodes})
        self.assertTrue(any('broken.py' in warning for warning in graph.warnings))
        self.assertEqual(next(n.summary for n in graph.nodes if n.id == 'valid'), 'Useful module.')

    def test_ignored_directories_and_symlinks(self):
        self.write('.venv/hidden.py', 'def hidden(): pass\n')
        self.write('actual.py', 'def visible(): pass\n')
        (self.root / 'linked.py').symlink_to(self.root / 'actual.py')
        graph = analyze(self.root)
        self.assertEqual({n.id for n in graph.nodes}, {'actual', 'actual:visible'})

    def test_unresolved_dynamic_calls_do_not_invent_edges(self):
        self.write('main.py', 'def run(obj):\n obj.unknown()\n print("hello")\n')
        graph = analyze(self.root)
        self.assertEqual(graph.edges, [])
        self.assertTrue(any('2 处调用' in warning for warning in graph.warnings))

    def test_entry_filter_terminates_on_cycles_and_excludes_unrelated_symbols(self):
        self.write('main.py', 'def a(): b()\ndef b(): a()\ndef unrelated(): pass\n')
        graph = analyze(self.root)
        diagram = to_mermaid(graph, 'calls', 'main:a')
        self.assertIn('main.py:1', diagram)
        self.assertIn('main.py:2', diagram)
        self.assertNotIn('unrelated', diagram)
        with self.assertRaises(ValueError):
            to_mermaid(graph, 'calls', 'main:missing')

    def test_json_contract_and_cli_export(self):
        self.write('main.py', 'def run(): pass\n')
        data = json.loads(to_json(analyze(self.root)))
        self.assertEqual(data['schema_version'], '1.0')
        self.assertTrue({'root', 'nodes', 'edges', 'warnings'} <= data.keys())
        output = self.root / 'reports' / 'modules.mmd'
        result = main(['analyze', str(self.root), '--format', 'mermaid', '-o', str(output)])
        self.assertEqual(result, 0)
        self.assertTrue(output.read_text().startswith('flowchart LR'))

    def test_missing_repository_fails_clearly(self):
        with self.assertRaises(ValueError):
            analyze(self.root / 'missing')


if __name__ == '__main__':
    unittest.main()
