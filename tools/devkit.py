"""Portable TS4 Access developer entry point. Builds never install into Mods."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition: raise RuntimeError(message)


def run(args, env, log=None):
    print('Running:', ' '.join(map(str, args)), flush=True)
    if log:
        with log.open('w', encoding='utf-8') as f:
            subprocess.run(list(map(str, args)), cwd=str(ROOT), env=env,
                           stdout=f, stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(list(map(str, args)), cwd=str(ROOT), env=env, check=True)


def environment():
    env = os.environ.copy()
    config = ROOT / 'dev.local.json'
    if config.is_file():
        for key, value in json.loads(config.read_text(encoding='utf-8-sig')).items():
            require(key in ('TS4_INSTALL', 'TS4_JAVA', 'TS4_FFDEC'), 'Unknown config key ' + key)
            if value: env[key] = str(value)
    return env


def doctor(env, full=False):
    require(sys.version_info[:2] == (3, 7), 'Use py -3.7 (the game needs Python 3.7 bytecode).')
    require(os.name == 'nt', 'This build kit targets Windows.')
    require('mods' not in [p.lower() for p in ROOT.parts], 'Keep the source kit outside Mods.')
    lock = json.loads((ROOT / 'reference/toolchain.json').read_text(encoding='utf-8'))
    require(shutil.which('node'), 'Install Node.js and reopen the terminal.')
    game = Path(env.get('TS4_INSTALL', ''))
    require(str(game) != '.' and (game / 'Data/Client/UI.package').is_file(),
            'Set TS4_INSTALL in dev.local.json to your Steam or EA game install folder.')
    require(sha(game / 'Data/Client/UI.package') == lock['game_ui_sha256'],
            'Game UI differs from the handoff baseline. Read GFX-SAFETY.md rebase instructions; do not override this check.')
    for filename in ('base.zip', 'core.zip', 'simulation.zip'):
        require((game / 'Data/Simulation/Gameplay' / filename).is_file(), 'Missing game archive ' + filename)
    for name, expected in lock['immutable_inputs'].items():
        p = ROOT / name
        require(p.is_file() and sha(p) == expected, 'Baseline input changed or missing: ' + name)
    print('Python, Node, game baseline and bundled reference inputs: OK', flush=True)
    if full:
        java = Path(env.get('TS4_JAVA', ''))
        jar = Path(env.get('TS4_FFDEC', ''))
        javac = java.with_name('javac.exe')
        require(java.is_file() and javac.is_file(), 'Set TS4_JAVA to java.exe from a JDK 21 installation (not a JRE).')
        require(jar.is_file(), 'Set TS4_FFDEC to ffdec.jar from the full portable FFDec distribution.')
        for rel, expected in lock['ffdec_files'].items():
            p = jar.parent / rel
            require(p.is_file() and sha(p) == expected,
                    'FFDec differs from the validated toolchain: ' + rel + '. Use the pinned release, including lib/.')
        version = subprocess.run([str(java), '-version'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True).stdout.decode('utf-8', 'replace')
        require('version "21.' in version, 'Use JDK 21 for the full UI build.')
        print(version.splitlines()[0], flush=True)
        print('JDK and pinned FFDec libraries: OK', flush=True)
    return lock


def verify_ui(final, chain, compat):
    from verify_v10_artifacts import (movie_map, replacement_sources, read_index,
        read_resource_bytes, noncode_tags, definitions)
    main_log = chain.read_text(encoding='utf-8-sig')
    require('fidelity gate PASSED' in main_log and 'CHAIN DONE' in main_log and 'CHAIN FAILED' not in main_log,
            'Main UI chain did not pass')
    require('compat fidelity gate PASSED' in compat.read_text(encoding='utf-8-sig'), 'Compatibility gate did not pass')
    result = {}
    for builder, package, work, prefix in (
        ('build_ui_package.py', 'tyjokr_ScreenReader_UI.package', 'work-1.128.90', 'patched_'),
        ('build_compat_package.py', 'tyjokr_ScreenReader_Compatibility_UICheats.package', 'work-compat', 'compat_')):
        movies = movie_map(ROOT / 'flash' / builder)
        replacements, _ = replacement_sources(work)
        require(set(replacements) == {(ROOT / 'flash' / work / 'gfx' / (prefix + n + '.swf')).resolve() for n in movies}, 'Unexpected movie set')
        path = ROOT / 'build' / package
        with path.open('rb') as f:
            entries = list(read_index(f)); actual = {e['instance']: read_resource_bytes(f, e) for e in entries}
        require(len(entries) == len(movies) and set(actual) == set(movies.values()), 'Package resource set differs')
        for name, instance in movies.items():
            movie = ROOT / 'flash' / work / 'gfx' / (prefix + name + '.swf')
            raw = movie.read_bytes()
            original = (ROOT / 'flash' / work / 'gfx' / ('ea_' + name + '.swf') if prefix == 'patched_' else
                        ROOT / 'flash/uicheats-base' / ('uic_' + name + '.swf'))
            before = original.read_bytes()
            require(actual[instance] == raw, 'Packaged resource mismatch: ' + name)
            require(noncode_tags(before) == noncode_tags(raw), 'Non-code GFX tags changed: ' + name)
            require(definitions(before) == definitions(raw), 'GFX class definitions changed: ' + name)
        shutil.copyfile(str(path), str(final / package))
        result[package] = {'movies': len(movies), 'sha256': sha(path)}
    (final / 'ui-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


def build(env, scripts_only=False):
    # A unique output and exclusive lock prevent crossed builds or stale manifests.
    (ROOT / 'build').mkdir(exist_ok=True)
    lockpath = ROOT / 'build/devkit.lock'
    try:
        with lockpath.open('x') as f: f.write(str(os.getpid()))
    except FileExistsError:
        raise RuntimeError('A build is running or was interrupted. If no build process remains, remove build/devkit.lock and retry.')
    try:
        lock = doctor(env, full=not scripts_only)
        from source_exchange import inventory
        source_frozen = inventory(ROOT)
        env['TS4_FFDEC_HELPERS'] = str(ROOT / 'build')
        if scripts_only:
            current = {n: hashlib.sha256(b).hexdigest() for n, b in inventory(ROOT).items() if n.startswith('flash/')}
            require(current == lock['flash_source'], 'UI source or build recipe changed. Use a full build.')
        shell = shutil.which('powershell')
        require(shell, 'Windows PowerShell is required')
        # The helper smoke test exercises the standalone EXE. Build it from
        # source before freezing inputs, so the kit need not ship that binary.
        run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'tools/build_prelaunch_helper.ps1'], env)
        from run_checks_v10 import input_hashes
        frozen = input_hashes()
        stamp = time.strftime('%Y%m%d_%H%M%S')
        final = ROOT / 'build' / ('devkit-' + stamp)
        final.mkdir()
        run([sys.executable, 'tools/run_checks_v10.py'], env)
        checks = json.loads((ROOT / 'build/v10-checks.json').read_text(encoding='utf-8'))
        require(checks['passed'] and checks['input_stable'], 'Regression report did not pass')
        require(frozen == input_hashes(), 'Source changed during tests. Stop edits and rebuild.')
        shutil.copyfile(str(ROOT / 'build/v10-checks.json'), str(final / 'v10-checks.json'))
        if scripts_only:
            for name in ('tyjokr_ScreenReader_UI.package', 'tyjokr_ScreenReader_Compatibility_UICheats.package'):
                shutil.copyfile(str(ROOT / 'reference/ui' / name), str(final / name))
            (final / 'ui-verification.json').write_text(json.dumps({'reused_reviewed_ui': True,
                  'baseline': lock['baseline_release']}), encoding='utf-8')
        else:
            java, jar = Path(env['TS4_JAVA']), Path(env['TS4_FFDEC'])
            run([java.with_name('javac.exe'), '-cp', jar, '-d', ROOT / 'build',
                 ROOT / 'tools/ReplaceScriptsBatch.java', ROOT / 'tools/ExportPcodeBatch.java'], env)
            tag = 'devkit-' + stamp
            run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'flash/chain.ps1', '-Tag', tag], env)
            gate = final / 'compat-gate.log'
            run([sys.executable, 'flash/gate_compat_pcode.py', 'flash/work-compat'], env, gate)
            chain = ROOT / 'flash' / ('chain-' + tag + '.log')
            verify_ui(final, chain, gate)
            shutil.copyfile(str(chain), str(final / 'chain.log'))
        require(frozen == input_hashes(), 'Source changed during build. Candidate rejected.')
        require(source_frozen == inventory(ROOT), 'Source or documentation changed during build. Candidate rejected.')
        shutil.copyfile(str(ROOT / 'flash/TooltipManager_patched.as'), str(final / 'TooltipManager_patched.as'))
        (final / 'flash-source-manifest.json').write_text(json.dumps(
            {n: hashlib.sha256(b).hexdigest() for n, b in source_frozen.items() if n.startswith('flash/')},
            indent=2), encoding='utf-8')
        run([sys.executable, 'tools/build_script_archive.py', final.relative_to(ROOT)], env)
        run([sys.executable, 'tools/stage_release.py', '--final', final, '--frozen', final / 'script-manifest.json'], env)
        print('Build complete. Test ZIPs are in the new dist folder. Nothing was installed or published.', flush=True)
    finally:
        lockpath.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    d = sub.add_parser('doctor'); d.add_argument('--full', action='store_true')
    b = sub.add_parser('build'); b.add_argument('--scripts-only', action='store_true')
    r = sub.add_parser('return'); r.add_argument('--summary', required=True); r.add_argument('--tests', required=True)
    v = sub.add_parser('review'); v.add_argument('archive', type=Path)
    s = sub.add_parser('setup'); s.add_argument('--uicheats', help='UI_Cheats_Extension.package (version 1.59.1)')
    args = parser.parse_args()
    if args.command == 'doctor': doctor(environment(), args.full)
    elif args.command == 'build': build(environment(), args.scripts_only)
    elif args.command == 'return':
        from source_exchange import make_return
        print(make_return(ROOT, args.summary, args.tests))
    elif args.command == 'setup':
        from setup_game_inputs import setup
        if not setup(environment(), args.uicheats): sys.exit(1)
    elif args.command == 'review':
        from source_exchange import review
        print(review(ROOT, args.archive))
    else: parser.error('choose setup, doctor, build, return or review')


if __name__ == '__main__':
    try: main()
    except (RuntimeError, ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        sys.exit('STOP: ' + str(exc))
