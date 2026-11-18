"""Check compiled handler parity across every patched TooltipManager copy.

Uses fresh exports produced by the fidelity gates. No game commands execute.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'flash'))
from gate_pcode import movie_list, own_only


def source_method(text, name):
    match = re.search(r'function\s+' + re.escape(name) + r'\([^\n]*\)[^{]*\{', text)
    if not match:
        raise ValueError('Missing source method: ' + name)
    start, pos, depth, quote, comment = match.start(), match.end(), 1, None, None
    while depth and pos < len(text):
        char, pair = text[pos], text[pos:pos + 2]
        if comment == '//':
            if char == '\n': comment = None
        elif comment == '/*':
            if pair == '*/': comment = None; pos += 1
        elif quote:
            if char == '\\': pos += 1
            elif char == quote: quote = None
        elif pair in ('//', '/*'):
            comment = pair; pos += 1
        elif char in ('"', "'"): quote = char
        elif char == '{': depth += 1
        elif char == '}': depth -= 1
        pos += 1
    if depth:
        raise ValueError('Unterminated method: ' + name)
    return text[start:pos].replace('\r\n', '\n')


def bodies(path, wanted, hashes=True):
    found, current, code, rows, exceptions = {}, None, False, [], []
    with path.open(encoding='utf-8') as stream:
        for raw in stream:
            line = raw.strip()
            match = re.match(r'(?:override )?(?:public|protected|private|internal)(?: static)? function (\w+)\(', line)
            if match:
                current = match[1] if match[1] in wanted else None
                code, rows, exceptions = False, [], []
            elif current and line == 'code': code = True
            elif current and code and line == 'end ; code':
                code = False
            elif current and not code and line.startswith('try from '):
                exceptions.append(line)
            elif current and line == 'end ; body':
                # Operand pool indices have variable encoded widths. Preserve
                # actual jump/exception destinations by mapping byte offsets
                # to instruction positions, rather than discarding targets.
                labels, instructions = {}, []
                for row in rows:
                    if re.fullmatch(r'ofs[0-9a-f]+:', row):
                        labels[row[:-1]] = len(instructions)
                    else:
                        instructions.append(row)
                def target(match):
                    if match[0] not in labels:
                        raise ValueError('Unresolved pcode label: ' + match[0])
                    return '@' + str(labels[match[0]])
                normalized = [re.sub(r'\bofs[0-9a-f]+\b', target, row) for row in instructions + exceptions]
                found[current] = hashlib.sha256('\n'.join(normalized).encode()).hexdigest() if hashes else normalized
                current, code = None, False
            elif current and code and line and not re.match(r'debug(?:file|line)?\b', line):
                # FFDec renumbers private script namespaces between movies.
                rows.append(re.sub(r'\.as\$\d+', '.as$SCRIPT', line))
    if set(found) != set(wanted):
        raise ValueError('Missing compiled methods in %s: %s' % (path, sorted(set(wanted) - set(found))))
    return found


def main():
    main_work, compat_work = Path(sys.argv[1]), Path(sys.argv[2])
    source = (ROOT / 'flash/TooltipManager_patched.as').read_text(encoding='utf-8-sig')
    registered = set(re.findall(r'AddMessageListenerByName\("A11y\w+",this\.(\w+)', source))
    wanted = registered | {'A11yInstallGameMessageHook', 'A11yOnGameMessage', 'A11yHandleEncoded',
                           'A11yScannerOwner', 'A11yGuardValid', 'A11yClickControl', 'A11yActivate'}
    old = subprocess.check_output(['git', 'show', 'HEAD:flash/TooltipManager_patched.as'], cwd=str(ROOT)).decode('utf-8-sig')
    for name in wanted:
        if source_method(source, name) != source_method(old, name):
            raise ValueError('Routing method changed from Git base: ' + name)
    for folder in ('Scripts', 'contrib-reference/modules'):
        subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', folder], cwd=str(ROOT), check=True)
        if subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', folder], cwd=str(ROOT)).strip():
            raise ValueError('Untracked game script in ' + folder)
    suffix = Path('scripts/olympus/core/TooltipManager.pcode')
    paths = [(name, main_work / 'pcode' / ('new_' + name) / suffix)
             for name in movie_list() if name not in own_only()]
    exports = sorted(compat_work.glob('compat-pcode-*'))
    if len(exports) != 1:
        raise ValueError('Choose an isolated compatibility work directory with one fresh gate export')
    paths += [('compat/' + path.name[4:], path / suffix) for path in sorted(exports[0].glob('new_*'))]
    reference = None
    for name, path in paths:
        actual = bodies(path, wanted)
        if reference is None: reference = actual
        if actual != reference:
            raise ValueError('Compiled handler mismatch: ' + name + ' / ' + ', '.join(k for k in wanted if actual[k] != reference[k]))
        print('Handlers match: ' + name, flush=True)
    result = {'passed': True, 'game_script_sources_unchanged': True,
              'git_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT)).decode().strip(),
              'normalization': 'Ignore debug metadata; normalize private script IDs and byte-offset labels to instruction positions, preserving jumps and exception ranges.',
              'routing_methods_unchanged_from_git_base': sorted(wanted),
              'compiled_copies': len(paths), 'method_hashes': reference}
    (main_work.parent / 'handler-audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('%d routing methods identical across %d compiled copies.' % (len(wanted), len(paths)))


if __name__ == '__main__':
    main()
