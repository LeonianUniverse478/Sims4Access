"""Check complete current-input rebuild structure and unchanged non-code tags."""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'flash'))
from extract_ea_movies import movies
from audit_ui_classes import definitions


def non_code(raw):
    if raw[:3] != b'GFX':
        raise ValueError('Expected uncompressed GFX')
    pos = 8 + (5 + 4 * (raw[8] >> 3) + 7) // 8 + 4
    result = [raw[8:pos]]
    while pos + 2 <= len(raw):
        start = pos
        header = struct.unpack_from('<H', raw, pos)[0]
        pos += 2
        size = header & 63
        if size == 63:
            size = struct.unpack_from('<I', raw, pos)[0]
            pos += 4
        end = pos + size
        if end > len(raw):
            raise ValueError('Truncated tag')
        if header >> 6 != 82:
            result.append(raw[start:end])
        pos = end
        if header >> 6 == 0:
            break
    result.append(raw[pos:])
    return result


def main():
    work = Path(sys.argv[1]).resolve()
    records = []
    for name in movies():
        original = (work / 'gfx' / ('ea_' + name + '.swf')).read_bytes()
        rebuilt = (work / 'gfx' / ('patched_' + name + '.swf')).read_bytes()
        if definitions(original) != definitions(rebuilt):
            raise SystemExit(name + ': class set changed')
        if non_code(original) != non_code(rebuilt):
            raise SystemExit(name + ': non-code tags changed')
        records.append({'movie': name, 'class_count': len(definitions(original)),
                        'non_code_tags_unchanged': True,
                        'input_sha256': hashlib.sha256(original).hexdigest(),
                        'output_sha256': hashlib.sha256(rebuilt).hexdigest()})
    result = {'movies': records, 'status': 'structural checks passed; bytecode gate and live testing separate'}
    (work / 'structure-report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('All %d movies retain their class sets and exact non-code tags.' % len(records))


if __name__ == '__main__':
    main()
