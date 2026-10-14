"""Every module the shipped scripts import must exist in the GAME's Python.

The game embeds a trimmed Python 3.7: its stdlib is base.zip, EA's code is
core.zip and simulation.zip, and some packages are simply absent (ctypes, which
we ship ourselves; concurrent). Offline tests run on a full Python and cannot
see this, so a missing module only shows up in game as a silently disabled
feature. An import passes when it is one of our modules, present in the game's
archives, already imported by the live-verified baseline source, or guarded by
an except ImportError. Run with py -3.7 tools/test_game_import_availability.py.
"""
import ast
import os
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'Scripts'
BASELINE = ROOT / 'build' / 'v14o-settings-script-candidate' / 'source' / 'Scripts'
if (ROOT / 'reference' / 'import-baseline').is_dir():
    BASELINE = ROOT / 'reference' / 'import-baseline'
GAMEPLAY = Path(os.environ.get('TS4_INSTALL', r'C:\Program Files\EA Games\The Sims 4')) / 'Data' / 'Simulation' / 'Gameplay'
_OPTIONAL = ('ImportError', 'ModuleNotFoundError')


def game_modules():
    """(modules, packages) the game can import from its own archives."""
    modules, packages = set(), set()
    for archive in ('base.zip', 'core.zip', 'simulation.zip'):
        for name in zipfile.ZipFile(str(GAMEPLAY / archive)).namelist():
            if not name.endswith(('.pyc', '.py')):
                continue
            if name.startswith('lib/'):
                name = name[4:]
            parts = name.rsplit('.', 1)[0].split('/')
            if parts[-1] == '__init__':
                parts = parts[:-1]
                packages.add('.'.join(parts))
            if parts:
                modules.add('.'.join(parts))
    return modules, packages


def own_modules(folder):
    modules, packages = set(), set()
    for path in folder.rglob('*.py'):
        parts = list(path.relative_to(folder).with_suffix('').parts)
        if parts[-1] == '__init__':
            parts = parts[:-1]
            packages.add('.'.join(parts))
        modules.add('.'.join(parts))
    return modules, packages


def _guarded(node, parents):
    for parent in parents:
        if isinstance(parent, ast.Try) and node in _body_nodes(parent):
            for handler in parent.handlers:
                names = []
                if isinstance(handler.type, ast.Name):
                    names = [handler.type.id]
                elif isinstance(handler.type, ast.Tuple):
                    names = [elt.id for elt in handler.type.elts if isinstance(elt, ast.Name)]
                if any(name in _OPTIONAL for name in names):
                    return True
    return False


def _body_nodes(try_node):
    found = set()
    for stmt in try_node.body:
        for sub in ast.walk(stmt):
            found.add(sub)
    return found


def imports(path, package=''):
    """[(module, line, guarded)] for every absolute import in a file."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue                      # relative: our own package
            names = [node.module]
        if not names:
            continue
        chain = []
        cursor = node
        while cursor in parents:
            cursor = parents[cursor]
            chain.append(cursor)
        guarded = _guarded(node, chain)
        found.extend((name, node.lineno, guarded) for name in names)
    return found


def available(name, modules, packages):
    if name in modules:
        return True
    top = name.split('.')[0]
    # "import os.path" style: an attribute of a plain module, not a subpackage.
    return top in modules and top not in packages


class GameImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (GAMEPLAY / 'base.zip').is_file():
            raise unittest.SkipTest('game archives not installed at {}'.format(GAMEPLAY))
        cls.modules, cls.packages = game_modules()
        own, own_packages = own_modules(SCRIPTS)
        cls.modules |= own
        cls.packages |= own_packages
        cls.proven = set()
        if BASELINE.is_dir():
            for path in BASELINE.rglob('*.py'):
                cls.proven.update(name for name, _, _ in imports(path))

    def missing(self, folder):
        problems = []
        for path in sorted(folder.rglob('*.py')):
            for name, line, guarded in imports(path):
                if guarded or name in self.proven or available(name, self.modules, self.packages):
                    continue
                problems.append('{}:{} imports {}'.format(path.relative_to(ROOT), line, name))
        return problems

    def test_game_archives_look_right(self):
        for name in ('threading', 'queue', 'os', 'sims4.commands', 'services', 'interactions.choices'):
            self.assertTrue(available(name, self.modules, self.packages), name)
        self.assertFalse(available('concurrent.futures', self.modules, self.packages))

    def test_every_shipped_import_exists_in_game(self):
        self.assertEqual(self.missing(SCRIPTS), [])

    def test_the_checker_catches_a_missing_package(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            probe = Path(folder) / 'probe.py'
            probe.write_text('import threading\nfrom concurrent.futures import Future\n'
                             'try:\n    import winsound\nexcept ImportError:\n    winsound = None\n'
                             'try:\n    import asyncio.tasks_nope\nexcept Exception:\n    pass\n',
                             encoding='utf-8')
            found = imports(probe)
            self.assertIn(('concurrent.futures', 2, False), found)
            self.assertIn(('winsound', 4, True), found)
            self.assertIn(('asyncio.tasks_nope', 8, False), found)   # a generic catch is not a guard


if __name__ == '__main__':
    unittest.main()
