"""Inventory literal Python -> Flash messages and Flash -> Python channels.

Unresolved literals require manual classification: local key commands and
encoded routes are not necessarily missing Flash functions.
"""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    flash_files = [ROOT / 'flash/TooltipManager_patched.as'] + list((ROOT / 'flash/extra-classes').glob('*.as'))
    handlers = {}
    methods = set()
    channels = set()
    for file in flash_files:
        text = file.read_text(encoding='utf-8-sig')
        methods.update(re.findall(r'function\s+(A11y\w+)\s*\(', text))
        for message, method in re.findall(r'AddMessageListener(?:ByName)?\("(A11y\w+)",this\.(\w+)', text):
            handlers.setdefault(message, []).append({'file': str(file.relative_to(ROOT)), 'method': method})
        channels.update(re.findall(r'"(a11y(?:plus)?\.[a-z_]+)"', text))
    literals = {}
    commands = set()
    for file in list((ROOT / 'Scripts').glob('*.py')) + list((ROOT / 'contrib-reference/modules').glob('*.py')):
        tree = ast.parse(file.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Str):
                if re.fullmatch(r'A11y\w+', node.s):
                    literals.setdefault(node.s, []).append('%s:%d' % (file.relative_to(ROOT), node.lineno))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'Command':
                if node.args and isinstance(node.args[0], ast.Str):
                    commands.add(node.args[0].s)
    result = {'registered_messages': handlers,
              'missing_handler_methods': sorted({item['method'] for entries in handlers.values() for item in entries} - methods),
              'python_message_literals': {name: {'locations': locations, 'registered': name in handlers}
                                          for name, locations in sorted(literals.items())},
              'flash_channels_without_literal_python_command': sorted(channels - commands),
              'note': 'Static inventory only. Encoded routes, startup dispatch, dynamic names and runtime ownership need separate review.'}
    local = {'A11yRepeat': 'tyjokr_a11y_keys._send -> speech.repeat_last',
             'A11ySpeechMode': 'tyjokr_a11y_keys._send -> speech.cycle_mode'}
    result['python_local_controls'] = local
    result['unclassified_python_literals'] = sorted(set(literals) - set(handlers) - set(local))
    output = ROOT / 'build/ui-port/bridge-inventory.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Registered messages:', len(handlers))
    print('Missing handler methods:', result['missing_handler_methods'])
    print('Unregistered Python literals:', ', '.join(name for name in sorted(literals) if name not in handlers))
    print('Flash channels without literal command:', result['flash_channels_without_literal_python_command'])
    print('Unclassified Python literals:', result['unclassified_python_literals'])


if __name__ == '__main__':
    main()
