"""Maintainer-only source kit assembly from a reviewed candidate and current sources.

    py -3.7 tools/make_source_kit.py --game <install> --ffdec <ffdec.jar>
        [--baseline <dist candidate>] [--reuse-proof <ui-verification.json or its folder>]
        [--output <folder>]

Works from the development tree and from an earlier kit (reference inputs are
taken from reference/ when the original workspace copies are absent). Every
textual file is redacted of private paths before the baseline is recorded,
and assembly stops if any remain.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from source_exchange import checkpoint, inventory  # noqa: E402

WORK = 'work-1.128.90'
GAME_VERSION = '1.128.90.1030'
GFX_TYPE = 0x62ECC59A
KIT_CLAUDE = Path('docs/development/kit/CLAUDE.md')
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.json', '.ps1', '.as', '.js', '.java', '.cs', '.tsv', '.cfg', '.ini'}
# Reviewed code is never rewritten: a private path there stops assembly instead.
CODE_SUFFIXES = {'.py', '.ps1', '.as', '.js', '.java', '.cs'}

_SEP = r'(?:\\\\|\\|/)+'
# A drive-letter or MSYS (/c/) Windows profile path, up to and including the user name.
USER_PATH = re.compile(r'(?i)(?:\b[a-z]:|(?<![\w.])/[a-z](?=/))' + _SEP + r'users' + _SEP + r'[^\\/\s"\'`<>|:*?]+')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _path_forms(path):
    """The spellings one absolute path takes in docs, JSON and MSYS shells."""
    text = str(path)
    forms = {text, text.replace('\\', '/'), text.replace('\\', '\\\\')}
    if len(text) > 2 and text[1] == ':':
        forms.add('/' + text[0].lower() + text[2:].replace('\\', '/'))
    return sorted(forms, key=len, reverse=True)


_PROFILE_FOLDERS = ('documents', 'desktop', 'pictures', 'music', 'videos')


def _onedrive_private(text):
    """Replace a folder path that follows the word OneDrive (someone's own
    layout) while keeping generic advice such as 'OneDrive Documents' or
    'OneDrive/localized Documents'. A quoted path needs two separators; a
    path attached to the word also must not start at a standard profile
    folder such as Documents."""
    out, pos = [], 0
    for m in re.finditer(r'(?i)onedrive', text):
        if m.start() < pos:
            continue
        start = m.end()
        rest = text[start:]
        quoted = re.match(r'[ \t]*([`\'"])', rest)
        if quoted:
            token_start = start + quoted.end()
            end = text.find(quoted.group(1), token_start)
            if end < 0 or '\n' in text[token_start:end]:
                continue
        elif rest[:1] in ('\\', '/'):
            token_start = start
            end = start + len(re.match(r'[^\s`\'"<>|]*', rest).group(0))
            first = text[token_start:end].strip('\\/').split('\\')[0].split('/')[0].lower()
            if first in _PROFILE_FOLDERS:
                continue
        else:
            continue
        token = text[token_start:end]
        if token.count('/') + token.count('\\') >= 2 and token != '<private-folder>':
            out.append(text[pos:token_start])
            out.append('<private-folder>')
            pos = end
    out.append(text[pos:])
    return ''.join(out)


def redact(text, originals):
    """originals: [(absolute path, placeholder)], most specific first."""
    for path, placeholder in originals:
        for form in _path_forms(path):
            text = re.sub(re.escape(form), lambda _m: placeholder, text, flags=re.I)
    text = USER_PATH.sub('<user-home>', text)
    return _onedrive_private(text)


def private_hits(text, code=False):
    """Remaining private paths. Code is checked for real user paths only, so
    test fixtures that mention generic OneDrive folders stay valid."""
    hits = [m.group(0) for m in USER_PATH.finditer(text)]
    if not code and _onedrive_private(text) != text:
        hits.append('OneDrive folder path')
    return hits


def redact_kit(kit, originals):
    """Rewrite non-code text in place; return every file that still leaks."""
    leaks = {}
    for p in sorted(kit.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = p.relative_to(kit).as_posix()
        raw = p.read_bytes()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            leaks[rel] = ['not UTF-8, cannot be checked']
            continue
        code = p.suffix.lower() in CODE_SUFFIXES
        if not code:
            cleaned = redact(text, originals)
            if cleaned != text:
                bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
                p.write_bytes(bom + cleaned.encode('utf-8'))
                text = cleaned
        hits = private_hits(text, code=code)
        if hits:
            leaks[rel] = hits
    return leaks


def pick(*candidates):
    """First existing path: the kit's own reference copy, then the original."""
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError('none of: ' + ', '.join(str(c) for c in candidates))


def recorded(value, release):
    """A path recorded by stage_release: absolute, project-relative, or a file
    that travelled with the candidate folder."""
    path = Path(value)
    for candidate in (path, ROOT / path, release / path.name):
        if candidate.exists():
            return candidate
    raise FileNotFoundError('recorded path not found: ' + str(value))


def check_scripts(root, frozen_sources):
    """Every runtime module, no more and no fewer, matches the reviewed build."""
    scripts = root / 'Scripts'
    current = {p.relative_to(scripts).as_posix(): sha(p) for p in scripts.rglob('*.py')
               if '__pycache__' not in p.parts}
    added = sorted(set(current) - set(frozen_sources))
    removed = sorted(set(frozen_sources) - set(current))
    changed = sorted(n for n in set(current) & set(frozen_sources) if current[n] != frozen_sources[n])
    if added or removed or changed:
        raise SystemExit('Runtime differs from the reviewed baseline. added={} removed={} changed={}'.format(
            added, removed, changed))


def check_flash(release, manifest):
    """Full Flash source set when the candidate recorded one; the template
    snapshot alone for older candidates (reported in toolchain.json)."""
    current = {n: hashlib.sha256(b).hexdigest() for n, b in inventory(ROOT).items() if n.startswith('flash/')}
    final = recorded(manifest['final_dir'], release) if 'final_dir' in manifest else release
    listed = final / 'flash-source-manifest.json'
    if listed.is_file():
        expected = json.loads(listed.read_text(encoding='utf-8'))
        if current != expected:
            added = sorted(set(current) - set(expected))
            removed = sorted(set(expected) - set(current))
            changed = sorted(n for n in set(current) & set(expected) if current[n] != expected[n])
            raise SystemExit('Flash sources differ from the reviewed candidate. added={} removed={} changed={}'.format(
                added, removed, changed))
        return 'full flash source manifest of ' + final.name
    snapshot = final / 'TooltipManager_patched.as'
    if not (snapshot.is_file() and snapshot.read_bytes() == (ROOT / 'flash/TooltipManager_patched.as').read_bytes()):
        raise SystemExit('UI template differs from the reviewed baseline')
    return 'template snapshot only (candidate predates flash-source-manifest.json)'


def check_ea_inputs(game, movies):
    """The kit's EA originals must be exactly the movies in --game's UI.package."""
    sys.path.insert(0, str(ROOT / 'tools' / 'vendor'))
    from dbpf_extract import read_index, read_resource_bytes
    wanted = {instance: name for name, instance in movies.items()}
    found = {}
    with (game / 'Data/Client/UI.package').open('rb') as f:
        for entry in list(read_index(f)):
            if entry['type'] == GFX_TYPE and entry['instance'] in wanted:
                found[wanted[entry['instance']]] = read_resource_bytes(f, entry)
    missing = sorted(set(movies) - set(found))
    differs = sorted(n for n in found
                     if found[n] != (ROOT / 'flash' / WORK / 'gfx' / ('ea_' + n + '.swf')).read_bytes())
    if missing or differs:
        raise SystemExit('EA inputs in flash/{}/gfx do not match --game. missing={} differs={}. '
                         'Re-extract and rebase before making a kit.'.format(WORK, missing, differs))


def reuse_proof(path, packages):
    """Record a full rebuild whose packages equal the reviewed ones that
    scripts-only builds reuse. A contradicting proof stops assembly."""
    if path is None:
        return None
    path = path / 'ui-verification.json' if path.is_dir() else path
    data = json.loads(path.read_text(encoding='utf-8'))
    data = data.get('packages', data)
    proof = {}
    for name, digest in packages.items():
        entry = data.get(name)
        if not isinstance(entry, dict) or entry.get('sha256') != digest:
            raise SystemExit('Reuse proof {} does not match reviewed {}'.format(path, name))
        proof[name] = digest
    return {'rebuilt_equal_to_reference': True, 'proof': path.parent.name + '/' + path.name, 'packages': proof}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'dist/2026-09-26_2209')
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--ffdec', type=Path, required=True)
    parser.add_argument('--reuse-proof', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    release = args.baseline.resolve()
    manifest = json.loads((release / 'RELEASE-MANIFEST.json').read_text(encoding='utf-8'))
    frozen = json.loads(recorded(manifest['frozen_manifest'], release).read_text(encoding='utf-8'))
    check_scripts(ROOT, frozen['sources'])
    flash_proof = check_flash(release, manifest)
    from verify_v10_artifacts import movie_map
    ui_movies = movie_map(ROOT / 'flash/build_ui_package.py')
    check_ea_inputs(args.game, ui_movies)
    # The maintainer tree keeps the template under docs; a kit carries it as
    # its root CLAUDE.md, so a kit can assemble the next kit too.
    template = pick(ROOT / KIT_CLAUDE, ROOT / 'CLAUDE.md')

    stamp = time.strftime('%Y-%m-%d_%H%M%S')
    out = (args.output or ROOT / 'dist' / ('source-kit-' + stamp)).resolve()
    if 'mods' in [part.lower() for part in out.parts]:
        raise SystemExit('Keep the source kit outside Mods.')
    kit = out / 'TS4_Access_Source'
    kit.mkdir(parents=True, exist_ok=False)
    included = set()

    def copy(src, relative=None):
        src = Path(src)
        relative = relative or src.relative_to(ROOT)
        dest = kit / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(dest))
        included.add(dest.relative_to(kit).as_posix())

    for name in ('compile.py', 'Dev.ps1', 'START-HERE.md', 'dev.local.example.json',
                 'README.txt', 'CONTROLS.txt', 'CHEATS.txt', 'README-SpeechPack.txt'):
        copy(ROOT / name)
    # The collaborator's assistant instructions live as a template, so they
    # never steer sessions in the maintainer's own tree.
    copy(template, Path('CLAUDE.md'))
    for folder, patterns in [('Scripts', ['*.py']), ('helper', ['*.cs', '*.ps1', '*.txt']),
                             ('docs', ['*.md']), ('prism', ['*'])]:
        for p in (ROOT / folder).rglob('*'):
            if p.relative_to(ROOT).as_posix().startswith(KIT_CLAUDE.parent.as_posix() + '/'):
                continue    # shipped once, as the kit's root CLAUDE.md
            if p.is_file() and '__pycache__' not in p.parts and any(p.match(x) for x in patterns): copy(p)
    # Current source tools plus transitive test helpers. Historical deploy and
    # game-control scripts are intentionally absent from the runnable toolset.
    files = {p.stem: p for p in (ROOT / 'tools').glob('*.py')}
    selected = set((ROOT / 'tools').glob('test_*.py'))
    selected.update(ROOT / 'tools' / n for n in ('devkit.py', 'source_exchange.py', 'make_source_kit.py',
        'build_script_archive.py', 'stage_release.py', 'run_checks_v10.py', 'verify_v10_artifacts.py'))
    queue = list(selected)
    while queue:
        p = queue.pop()
        for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
            names = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else (
                [node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                if name in files and files[name] not in selected:
                    selected.add(files[name]); queue.append(files[name])
    for pattern in ('test_*.js', 'test_*.ps1', '*.as'):
        selected.update((ROOT / 'tools').glob(pattern))
    selected.update(ROOT / 'tools' / n for n in ('ReplaceScriptsBatch.java', 'ExportPcodeBatch.java', 'build_prelaunch_helper.ps1'))
    selected.update((ROOT / 'tools/vendor').glob('*.py'))
    for p in selected: copy(p)
    for name in ('chain.ps1', 'rebuild_all.ps1', 'build_uicheats_compat.ps1', 'gate_pcode.py',
                 'gate_compat_pcode.py', 'build_ui_package.py', 'build_compat_package.py',
                 'extract_ea_movies.py', 'extract_uicheats_bases.py', 'flash_config.py',
                 'flash_config.ps1', 'TooltipManager_patched.as'):
        copy(ROOT / 'flash' / name)
    for p in (ROOT / 'flash/extra-classes').glob('*.as'): copy(p)
    # Reproducibility inputs, not editable sources; these stay out of return ZIPs.
    for name in ui_movies:
        copy(ROOT / 'flash' / WORK / 'gfx' / ('ea_' + name + '.swf'))
    for name in movie_map(ROOT / 'flash/build_compat_package.py'):
        copy(ROOT / 'flash/uicheats-base' / ('uic_' + name + '.swf'))
    (kit / 'flash' / WORK / 'SOURCE.txt').write_text(
        'EA UI originals for game {}, used by the reviewed 25-movie baseline.\n'
        'Private development inputs. Source is the game Data/Client/UI.package.\n'
        'See reference/toolchain.json for exact hashes.\n'.format(GAME_VERSION), encoding='utf-8')
    (kit / 'flash/uicheats-base/SOURCE.txt').write_text(
        'Six UI Cheats Extension v1.59.1 baseline movies from the existing development workspace.\n'
        'Original extraction recorded 2026-08-28. Third-party/game rights remain with their owners.\n'
        'Private development inputs, not a new license grant. Rebase after UI Cheats changes.\n', encoding='utf-8')
    reviewed = {}
    for old, new in [('TS4_Access_UI.package', 'tyjokr_ScreenReader_UI.package'),
                     ('TS4_Access_Compatibility_UICheats.package', 'tyjokr_ScreenReader_Compatibility_UICheats.package')]:
        src = release / ('main/TS4_Access' if 'Compatibility' not in old else 'compat') / old
        assert sha(src) == manifest['files'][old]['sha256']
        copy(src, Path('reference/ui') / new)
        reviewed[new] = sha(src)
    # A kit carries its own copies of these; the original workspace is the fallback.
    import_baseline = pick(ROOT / 'reference/import-baseline',
                           ROOT / 'build/v14o-settings-script-candidate/source/Scripts')
    for p in import_baseline.rglob('*.py'):
        copy(p, Path('reference/import-baseline') / p.relative_to(import_baseline))
    copy(pick(ROOT / 'reference/ui-movie-names.tsv', ROOT.parents[1] / 'screen-reader-research/ui-movie-names.tsv'),
         Path('reference/ui-movie-names.tsv'))
    for name in ('HOTFIX-QA.md', 'CLAUDE-REVIEW.md', 'RELEASE-MANIFEST.json', 'ui-verification.json'):
        if (release / name).is_file():
            copy(release / name, Path('reference') / name)
    # Historical technical knowledge is clearly separated from current workflow.
    for p in ROOT.glob('*.md'):
        if p.name in ('START-HERE.md', 'CLAUDE.md', 'README-proposed.txt', 'COLLAB-CLAUDE-CODEX.md'): continue
        text = p.read_text(encoding='utf-8-sig', errors='replace')
        dest = kit / 'docs/development/history' / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.\n\n' + text, encoding='utf-8')
    (kit / '.gitignore').write_text('dev.local.json\nbuild/\ndist/\nexchange/\nreviews/\n__pycache__/\n*.pyc\n'
        'flash/work-*/\nflash/uicheats-base/\nreference/\n.handoff/\nprism/\n*.log\nhelper/*.exe\n', encoding='utf-8')

    # Private paths go before anything is hashed or recorded as the baseline.
    originals = [(ROOT, '<original-project>'), (ROOT.parents[1], '<original-workspace>')]
    leaks = redact_kit(kit, originals)
    if leaks:
        for rel, hits in sorted(leaks.items()):
            print('PRIVATE PATH', rel, hits[:2])
        raise SystemExit('Private paths remain in {} file(s); the kit at {} is incomplete and must not be sent.'.format(
            len(leaks), kit))

    immutable = {}
    for parent in ['reference/ui', 'reference/import-baseline', 'flash/' + WORK + '/gfx', 'flash/uicheats-base', 'prism']:
        for p in (kit / parent).rglob('*'):
            if p.is_file(): immutable[p.relative_to(kit).as_posix()] = sha(p)
    live = False
    if (release / 'ui-verification.json').is_file():
        live = json.loads((release / 'ui-verification.json').read_text(encoding='utf-8')).get('live_verified') is True
    toolchain = {'game_version': GAME_VERSION, 'baseline_release': release.name,
        'live_verified': live,
        'live_status': ('The candidate record says live verified; see reference/HOTFIX-QA.md.' if live else
                        'Reviewed offline only; not live verified.'),
        'flash_source_proof': flash_proof,
        'ui_reuse_proof': reuse_proof(args.reuse_proof, reviewed),
        'python': '3.7.9', 'node_tested': '24.14.1', 'jdk_tested': 'Temurin 21.0.11+10',
        'ffdec': '26.2.1', 'game_ui_sha256': sha(args.game / 'Data/Client/UI.package'),
        'immutable_inputs': immutable,
        'ffdec_files': {p.relative_to(args.ffdec.parent).as_posix(): sha(p) for p in
                       [args.ffdec] + sorted((args.ffdec.parent / 'lib').glob('*.jar'))},
        'flash_source': {n: hashlib.sha256(b).hexdigest() for n, b in inventory(kit).items() if n.startswith('flash/')}}
    (kit / 'reference/toolchain.json').write_text(json.dumps(toolchain, indent=2), encoding='utf-8')
    base = checkpoint(kit)
    all_files = {p.relative_to(kit).as_posix(): sha(p) for p in sorted(kit.rglob('*')) if p.is_file()}
    (out / 'KIT-MANIFEST.json').write_text(json.dumps({'baseline_id': base['id'], 'files': all_files}, indent=2), encoding='utf-8')
    archive = out / ('TS4_Access_Source_' + stamp + '.zip')
    with zipfile.ZipFile(str(archive), 'x', zipfile.ZIP_DEFLATED) as z:
        for n in sorted(all_files): z.write(str(kit / n), 'TS4_Access_Source/' + n)
    (out / 'SHA256.txt').write_text(sha(archive) + '  ' + archive.name + '\n', encoding='utf-8')
    print(archive)
    print('Files:', len(all_files), 'Bytes:', archive.stat().st_size, 'Baseline:', base['id'])


if __name__ == '__main__': main()
