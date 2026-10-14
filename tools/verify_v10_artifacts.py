"""Historical V10 verifier; shared helpers are still used by regression tests.

Do not run main() for current releases: it has old paths and a 24-movie scope.
Use tools/devkit.py build for current 25+6 artifact validation.
"""
import ast
import hashlib
import importlib.util
import json
import marshal
from pathlib import Path
import re
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'vendor'))
from dbpf_extract import read_index, read_resource_bytes
from audit_ui_classes import definitions
from run_checks_v10 import input_hashes, test_paths, check_count


def noncode_tags(raw):
    """Preserve graphics/timelines/imports byte for byte, not just opcodes."""
    start = 8 + (5 + 4 * (raw[8] >> 3) + 7) // 8 + 4
    result = [(None, raw[:4] + raw[8:start])]
    pos = start
    while pos + 2 <= len(raw):
        header = struct.unpack_from('<H', raw, pos)[0]
        pos += 2
        size = header & 63
        if size == 63:
            size = struct.unpack_from('<I', raw, pos)[0]
            pos += 4
        body = raw[pos:pos + size]
        assert len(body) == size, 'truncated movie tag'
        pos += size
        tag = header >> 6
        if tag != 82:
            result.append((tag, body))
        if tag == 0:
            break
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def movie_map(script):
    source = script.read_text(encoding='utf-8')
    body = re.search(r'MOVIES\s*=\s*\{(.*?)\n\}', source, re.S).group(1)
    return ast.literal_eval('{' + re.sub(r'#.*', '', body) + '}')


def verify_checks(build):
    report_path = build / 'v10-checks.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['passed'] and report['input_stable'], 'regression checks did not pass on stable inputs'
    assert report['inputs'] == input_hashes(), 'regression checks predate current source'
    results = report['results']
    expected = {path.relative_to(ROOT).as_posix() for path in test_paths()}
    assert len(results) == len(expected) and {item['suite'] for item in results} == expected, 'suite set mismatch'
    paths = [report_path] + [ROOT / relative for relative in sorted(report['inputs'])]
    for item in results:
        assert item['passed'] and item['returncode'] == 0 and item['checks'] > 0, item['suite']
        path = ROOT / item['log']
        assert path == build / ('v10-' + Path(item['suite']).stem + '.log'), 'unexpected check log'
        assert sha(path) == item['log_sha256'], item['suite'] + ': log changed'
        assert check_count(path.read_text(encoding='utf-8')) == item['checks'], item['suite'] + ': count mismatch'
        paths.append(path)
    print('Regression: {} checks across {} Python/AS source fixture suites'.format(
        sum(item['checks'] for item in results), len(results)))
    return paths


def replacement_sources(work):
    manifest = ROOT / 'flash' / work / 'replace-batch.tsv'
    result = {}
    for line in manifest.read_text(encoding='utf-8-sig').splitlines():
        fields = line.split('\t')
        assert len(fields) >= 4 and len(fields) % 2 == 0, 'invalid Flash replacement manifest'
        output = Path(fields[1]).resolve()
        assert output not in result, 'duplicate Flash replacement output'
        sources = [Path(value).resolve() for value in fields[3::2]]
        for source in sources:
            assert source.is_file(), 'replacement source missing: ' + str(source)
            assert output.stat().st_mtime_ns >= source.stat().st_mtime_ns, 'movie predates source: ' + str(source)
        result[output] = sources
    return result, manifest


def main():
    assert sys.version_info[:2] == (3, 7), 'must verify with Python 3.7'
    build = ROOT / 'build'
    chain = ROOT / 'flash/chain-keyboard-v10-final.log'
    compat_gate = ROOT / 'flash/gate-compat-v10.log'
    chain_text = chain.read_text(encoding='utf-8-sig')
    compat_text = compat_gate.read_text(encoding='utf-8-sig')
    assert 'fidelity gate PASSED' in chain_text and 'CHAIN DONE' in chain_text and 'CHAIN FAILED' not in chain_text
    assert 'compat fidelity gate PASSED' in compat_text
    checked_paths = verify_checks(build)
    baseline_path = build / 'v10-preserved-baseline.json'
    baseline = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
    assert len(baseline) == 6, 'expected named save, cfg and four release artifacts'
    for preserved_path, expected_hash in baseline.items():
        assert sha(Path(preserved_path)).lower() == expected_hash.lower(), 'preserved file changed: ' + preserved_path
    compat_package = build / 'tyjokr_ScreenReader_Compatibility_UICheats.package'
    assert compat_gate.stat().st_mtime >= compat_package.stat().st_mtime, 'compat gate predates rebuilt package'
    archive = build / 'tyjokr_ScreenReader.ts4script'
    sources = sorted((ROOT / 'Scripts').rglob('*.py'))
    with zipfile.ZipFile(str(archive)) as zf:
        expected = set()
        for path in sources:
            relative = path.relative_to(ROOT / 'Scripts').as_posix()
            member = relative[:-3] + '.pyc'
            expected.add(member)
            blob = zf.read(member)
            assert blob[:4] == importlib.util.MAGIC_NUMBER, member
            code = compile(path.read_text(encoding='utf-8'), relative, 'exec', optimize=2)
            # marshal records string interning/reference state, which can
            # differ between interpreter processes for identical bytecode.
            archived = marshal.loads(blob[16:])
            assert archived == code and archived.co_filename == relative, member + ': source mismatch'
        assert set(zf.namelist()) == expected, 'archive member set mismatch'
    print('Script: {} Python 3.7 modules match current source'.format(len(sources)))
    packages = []
    for builder, package, work, prefix in (
            ('build_ui_package.py', 'tyjokr_ScreenReader_UI.package', 'work-1.127.41', 'patched_'),
            ('build_compat_package.py', 'tyjokr_ScreenReader_Compatibility_UICheats.package', 'work-compat', 'compat_')):
        movies = movie_map(ROOT / 'flash' / builder)
        if prefix == 'compat_':
            assert movies == {
                'TimeControls': 0xC4B030271AE45C30, 'ClassLibraryOlympus': 0x3FFE72432A703655,
                'SimInfoTray': 0x5FFB8AE26BC11E96, 'SimInfoMotivePanel': 0x093958A845E285BA,
                'SimHub': 0xCC47BCC1ABF46007, 'PickersPurchase': 0x3EEF420EE17FE553,
            }, 'compatibility override scope changed'
        path = build / package
        replacements, replacement_manifest = replacement_sources(work)
        expected_outputs = {(ROOT / 'flash' / work / 'gfx' / (prefix + name + '.swf')).resolve() for name in movies}
        assert set(replacements) == expected_outputs, package + ': replacement movie set mismatch'
        checked_paths.append(replacement_manifest)
        assert chain.stat().st_mtime_ns >= path.stat().st_mtime_ns, 'main pipeline log predates package'
        with path.open('rb') as fh:
            entries = list(read_index(fh))
            actual = {e['instance']: read_resource_bytes(fh, e) for e in entries}
        assert len(entries) == len(movies) and set(actual) == set(movies.values()), package
        caption_movies = 0
        for name, instance in movies.items():
            movie = ROOT / 'flash' / work / 'gfx' / (prefix + name + '.swf')
            raw = movie.read_bytes()
            assert path.stat().st_mtime_ns >= movie.stat().st_mtime_ns, name + ': movie was rebuilt after package'
            if prefix == 'compat_':
                assert compat_gate.stat().st_mtime_ns >= movie.stat().st_mtime_ns, name + ': compatibility gate predates movie'
            assert actual[instance] == raw, name + ': package differs from built movie'
            original = (ROOT / 'flash' / 'work-1.127.41' / 'gfx' / ('ea_' + name + '.swf')
                        if prefix == 'patched_' else ROOT / 'flash' / 'uicheats-base' / ('uic_' + name + '.swf'))
            before = original.read_bytes()
            assert noncode_tags(before) == noncode_tags(raw), name + ': non-code movie content changed'
            assert definitions(before) == definitions(raw), name + ': class definition set changed'
            if name == 'AgeUpPanel':
                assert b'A11yFocusPanel' in raw and b'A11yDismissPanel' in raw, 'AgeUp hook missing'
            if name in ('SimInfoTray', 'SimInfoMotivePanel'):
                assert b'A11yMotiveText' in raw, name + ': final V10 need narration missing'
            if name != 'AgeUpPanel' and b'TooltipManager' in raw:
                for symbol in (b'A11yShowCaption', b'A11yHideCaption', b'A11yCaptionFrame',
                               b'A11yCaptionResize', b'A11yLayoutCaption', b'mA11yCaptionText',
                               b'A11yModalFrame', b'A11yTopModalWidget', b'A11yRevealIndex', b'A11yDrainNav',
                               b'A11yInstallKeyGuards', b'A11yGuardValid', b'A11yTabControl',
                               b'A11yFocusSettled', b'A11yInformational', b'A11yOpenHud',
                               b'A11yCalendarSchedule', b'A11yPhoneFrame',
                               b'A11yGridLayout', b'A11yGridStep', b'A11yKeyboardDecoration',
                               b'A11yCurrentDropdown', b'A11yFocusDropdown', b'A11yGroupOwner',
                               b'A11yActionProxy', b'A11yAnnounceScope', b'A11yTextValue',
                               b'A11yFundsTarget', b'A11ySetSilentMood', b'mA11yOwnerReported',
                               b'A11ySemanticTarget', b'A11yFilterPopup', b'A11yKeyboardSuppress',
                               b'A11yInitialFocus', b'A11yPhonePage', b'A11yCalendarBusy',
                               b'A11yCompleted', b'mA11ySyntheticHover',
                               b'A11yEscape', b'A11yIndexMotiveLinks', b'A11ySingleFilterLabel',
                               b'A11yInspect', b'mA11yRingBounds', b'A11yWorldHudMode',
                               b'mA11yHudMode', b'mA11yScopeReadyAt', b'A11yNativeTab', b'mA11yNativeTabDirection',
                               b'A11yStartupInstall', b'A11yStartupWrite', b'A11yStartupDrainKeys',
                               b'A11yStartupData', b'A11yStartupFrame', b'A11yPostToPython', b'mA11yStartupFence',
                               b'A11yBuildAim', b'A11yBuildProjectionFrame', b'A11yBuildCommand',
                               b'A11yBuildBlocked', b'A11yBuildEnable', b'A11yBuildProduct', b'A11yBuildError',
                               b'A11yKeyProbeOn', b'A11yKeyProbeOff', b'A11yKeyProbeStageEvent',
                               b'A11yFenceOpeningInput', b'A11yCalendarAddOwner', b'A11yTextDecoration'):
                    assert symbol in raw, name + ': missing V10 symbol ' + str(symbol)
                caption_movies += 1
                template = ROOT / 'flash' / 'TooltipManager_patched.as'
                generated = ROOT / 'flash' / work / 'gfx' / (('ttm_' if prefix == 'patched_' else 'ttm_compat_') + name + '.as')
                # PS 5.1's existing builder can re-encode punctuation in
                # comment-only lines. Require identical executable source.
                code_lines = lambda text: [line for line in text.splitlines()
                                           if not line.lstrip().startswith('//')]
                expected = template.read_text(encoding='utf-8').replace('A11YLIBNAME', name)
                assert code_lines(expected) == code_lines(generated.read_text(encoding='utf-8-sig')), name + ': stale generated template'
                assert movie.stat().st_mtime_ns >= template.stat().st_mtime_ns, name + ': movie predates current template'
                checked_paths.append(generated)
        print('{}: {} resources round-trip; navigation/caption symbols in {} movies'.format(package, len(movies), caption_movies))
        packages.append(path)
    inventory = json.loads((build / 'ui-class-audit-v6.json').read_text())
    shipping = json.loads((build / 'v6-shipping-movies.json').read_text())
    original = movie_map(build / 'source-before-v6/build_ui_package.py')
    assert set(shipping) == set(original) | {'AgeUpPanel'} and len(shipping) == 24, 'shipping scope expanded'
    assert movie_map(ROOT / 'flash/build_ui_package.py') == shipping, 'shipping map mismatch'
    assert not any(name.startswith('CAS') or name == 'EngagementLibrary' for name in shipping), 'excluded movie shipped'
    assert set(shipping) <= set(inventory['definitions']['olympus.core.TooltipManager']), 'inventory mismatch'
    paths = sources + [ROOT / 'flash' / 'TooltipManager_patched.as', ROOT / 'flash' / 'chain.ps1',
                       ROOT / 'flash' / 'gate_compat_pcode.py',
                       ROOT / 'tools' / 'test_scanner_v5.py', ROOT / 'tools' / 'test_navigation_v6.py',
                       ROOT / 'flash' / 'gate_pcode.py', ROOT / 'flash' / 'rebuild_all.ps1',
                       ROOT / 'flash' / 'build_ui_package.py', ROOT / 'tools' / 'ExportPcodeBatch.java',
                       ROOT / 'flash' / 'build_uicheats_compat.ps1', ROOT / 'flash' / 'build_compat_package.py',
                       ROOT / 'tools' / 'ReplaceScriptsBatch.java', ROOT / 'build' / 'ReplaceScriptsBatch.class',
                       ROOT / 'build' / 'ExportPcodeBatch.class', archive] + packages
    paths += sorted((ROOT / 'flash' / 'extra-classes').glob('*.as'))
    paths += sorted((build).glob('ExportPcodeBatch$*.class'))
    paths += checked_paths
    paths += sorted(path for path in (ROOT / 'tools').glob('*v10*') if path.is_file())
    paths += [build / 'v10-preserved-baseline.json']
    paths += [ROOT / 'tools/verify_v10_artifacts.py', ROOT / 'tools/deploy_v10.ps1',
              build / 'v10-source.diff', ROOT / 'tools/audit_ui_classes.py',
              ROOT / 'tools/test_feedback_v9.py', ROOT / 'tools/test_scanner_performance_v9_3.py', ROOT / 'tools/test_feedback_v8.py', ROOT / 'tools/test_keyboard_v7.py', ROOT / 'tools/test_hub_v7.py',
              ROOT / 'tools/test_settings_cfg.py', ROOT / 'tools/test_speech_modes.py', ROOT / 'tools/test_inventory_names_v9_6.py',
              ROOT / 'flash/chain-keyboard-v10-final.log', ROOT / 'flash/gate-compat-v10.log',
              build / 'ui-class-audit-v6.json', build / 'v6-shipping-movies.json',
              build / 'source-before-v6/build_ui_package.py']
    paths += test_paths()
    manifest = {p.relative_to(ROOT).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(set(paths))}
    (build / 'v10-verification.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Wrote build/v10-verification.json')


if __name__ == '__main__':
    main()
