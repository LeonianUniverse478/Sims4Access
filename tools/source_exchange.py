"""Source-only handoff snapshots and review bundles. Never installs or merges."""
import argparse
import difflib
import hashlib
import json
import re
import time
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {'compile.py', 'Dev.ps1', 'START-HERE.md', 'CLAUDE.md',
              'README.txt', 'CONTROLS.txt', 'CHEATS.txt', 'README-SpeechPack.txt',
              'dev.local.example.json', '.gitignore'}
PREFIXES = ('Scripts/', 'tools/', 'docs/', 'helper/')
SUFFIXES = {'.py', '.as', '.js', '.ps1', '.java', '.cs', '.md', '.txt', '.json'}
MAX_BYTES = 64 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def allowed(name):
    if not isinstance(name, str):
        return False
    p = PurePosixPath(name)
    if not name or any(ord(c) < 32 or c in '\\:*?"<>|' for c in name) or p.is_absolute():
        return False
    if any(x in ('', '.', '..') or x.endswith(('.', ' ')) or
           re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', x)
           for x in name.split('/')):
        return False
    if '__pycache__' in p.parts or '.git' in p.parts:
        return False
    if name in ROOT_FILES:
        return True
    if p.suffix.lower() not in SUFFIXES:
        return False
    if name.startswith(PREFIXES):
        return True
    return name.startswith('flash/extra-classes/') or (name.startswith('flash/') and len(p.parts) == 2)


def inventory(root):
    result = {}
    for top in ['Scripts', 'tools', 'docs', 'helper', 'flash']:
        paths = ((list((root / 'flash').glob('*')) + list((root / 'flash/extra-classes').rglob('*')))
                 if top == 'flash' else (root / top).rglob('*'))
        for p in paths:
            name = p.relative_to(root).as_posix()
            if allowed(name) and p.is_file():
                if p.is_symlink() or root.resolve() not in p.resolve().parents:
                    raise ValueError('Source links are not supported: ' + name)
                result[name] = p.read_bytes()
    for name in ROOT_FILES:
        p = root / name
        if p.is_file():
            if p.is_symlink():
                raise ValueError('Source links are not supported: ' + name)
            result[name] = p.read_bytes()
    return result


def checkpoint(root):
    """Used only when preparing a fresh handoff, not before returning edits."""
    data = inventory(root)
    manifest = {'format': 1, 'files': {n: digest(b) for n, b in sorted(data.items())}}
    manifest['id'] = digest(json.dumps(manifest, sort_keys=True).encode())
    out = root / '.handoff'
    out.mkdir(exist_ok=True)
    if (out / 'baseline.json').exists():
        raise ValueError('Baseline exists. Prepare a NEW handoff folder after review.')
    with zipfile.ZipFile(str(out / 'baseline.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in sorted(data.items()):
            z.writestr(n, b)
    (out / 'baseline.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def baseline(root):
    manifest = json.loads((root / '.handoff/baseline.json').read_text(encoding='utf-8'))
    identity = {'format': manifest['format'], 'files': manifest['files']}
    if digest(json.dumps(identity, sort_keys=True).encode()) != manifest['id']:
        raise ValueError('Baseline identity damaged')
    with zipfile.ZipFile(str(root / '.handoff/baseline.zip')) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_BYTES:
            raise ValueError('Baseline too large')
        data = {n: z.read(n) for n in z.namelist()}
    if {n: digest(b) for n, b in data.items()} != manifest['files'] or not all(map(allowed, data)):
        raise ValueError('Baseline snapshot damaged')
    return manifest, data


def unified(old, new, name):
    a = old.decode('utf-8-sig') if old is not None else ''
    b = new.decode('utf-8-sig') if new is not None else ''
    for line in difflib.unified_diff(a.splitlines(True), b.splitlines(True),
            fromfile='a/' + name if old is not None else '/dev/null',
            tofile='b/' + name if new is not None else '/dev/null'):
        yield line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'


def make_return(root, summary, tests, output=None):
    base, before = baseline(root)
    after = inventory(root)
    changes = []
    diff = []
    for n in sorted(set(before) | set(after)):
        if before.get(n) == after.get(n):
            continue
        old, new = before.get(n), after.get(n)
        changes.append({'path': n, 'before': digest(old) if old is not None else None,
                        'after': digest(new) if new is not None else None})
        # Sources must stay textual; binaries belong in separate test artifacts.
        diff.extend(unified(old, new, n))
    if not changes:
        raise ValueError('No source changes to return')
    manifest = {'format': 1, 'baseline_id': base['id'], 'summary': summary,
                'testing': tests, 'changes': changes}
    out = output or root / 'exchange' / ('TS4_Access_changes_' + time.strftime('%Y%m%d_%H%M%S') + '.zip')
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(out), 'x', zipfile.ZIP_DEFLATED) as z:
        z.writestr('RETURN.json', json.dumps(manifest, indent=2))
        z.writestr('CHANGES.patch', ''.join(diff))
        z.writestr('SUMMARY.md', '# Changes\n\n' + summary + '\n\n# Testing\n\n' + tests + '\n')
        for c in changes:
            if c['after'] is not None:
                z.writestr('files/' + c['path'], after[c['path']])
    return out


def review(root, archive, output=None):
    try:
        return _review(root, archive, output)
    except (KeyError, TypeError, AttributeError, UnicodeError, zipfile.BadZipFile) as exc:
        raise ValueError('Malformed return or baseline: ' + str(exc)) from exc


def _review(root, archive, output=None):
    base, before = baseline(root)
    baseline_spelling = {n.lower(): n for n in before}
    with zipfile.ZipFile(str(archive)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > MAX_BYTES:
            raise ValueError('Duplicate ZIP entries or oversized return')
        m = json.loads(z.read('RETURN.json').decode('utf-8'))
        if m.get('format') != 1 or m.get('baseline_id') != base['id']:
            raise ValueError('Different handoff baseline. Review against the original source kit.')
        expected = {'RETURN.json', 'CHANGES.patch', 'SUMMARY.md'}
        payload = {}
        seen = set()
        if not isinstance(m['changes'], list) or not m['changes']:
            raise ValueError('Return must contain a nonempty change list')
        for c in m['changes']:
            n = c['path']
            if not allowed(n) or n.lower() in seen:
                raise ValueError('Invalid or duplicate source path: ' + str(n))
            if baseline_spelling.get(n.lower(), n) != n:
                raise ValueError('Case-variant baseline path: ' + n)
            seen.add(n.lower())
            if c['before'] != base['files'].get(n):
                raise ValueError('Before hash differs from the trusted baseline: ' + n)
            if c['after'] is not None:
                expected.add('files/' + n)
                payload[n] = z.read('files/' + n)
                payload[n].decode('utf-8-sig')
                if digest(payload[n]) != c['after']:
                    raise ValueError('Payload hash mismatch: ' + n)
            elif c['before'] is None:
                raise ValueError('Deletion without a baseline file')
        if set(names) != expected:
            raise ValueError('Unexpected ZIP members')
    # Extract only after EVERY member and hash has been validated. No code runs.
    out = output or root / 'reviews' / time.strftime('%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=False)
    lines = ['# Source review', '', 'No working source was changed. Returned code has not been executed.', '',
             'Contributor summary (untrusted text):', '', str(m['summary']), '',
             'Contributor testing report (not independently verified):', '', str(m['testing']), '',
             '| File | Local status | Returned change |', '| --- | --- | --- |']
    patch = []
    conflicts = 0
    for c in m['changes']:
        n = c['path']
        p = root / n
        if p.is_symlink() or (p.exists() and root.resolve() not in p.resolve().parents):
            local = 'unsafe-local-link'
        else:
            local = digest(p.read_bytes()) if p.is_file() else None
        conflict = local not in (c['before'], c['after'])
        conflicts += int(conflict)
        change = 'delete' if c['after'] is None else ('add' if c['before'] is None else 'modify')
        lines.append('| {} | {} | {} |'.format(n, 'CONFLICT' if conflict else 'clean', change))
        patch.extend(unified(before.get(n), payload.get(n), n))
        if n in payload:
            target = out / 'files' / n
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload[n])
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out / 'CHANGES.patch').write_bytes(''.join(patch).encode('utf-8'))
    (out / 'RETURN.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
    return out, conflicts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command')
    r = sub.add_parser('return'); r.add_argument('--summary', required=True); r.add_argument('--tests', required=True)
    v = sub.add_parser('review'); v.add_argument('archive', type=Path)
    args = p.parse_args()
    if args.command == 'return': print(make_return(ROOT, args.summary, args.tests))
    elif args.command == 'review': print(review(ROOT, args.archive))
    else: p.error('choose return or review')


if __name__ == '__main__':
    main()
