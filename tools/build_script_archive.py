"""Compile Scripts/*.py into a ts4script WITHOUT deploying (same recipe as the
V11 candidate builder: Python 3.7, optimize=2, timestamp-less pyc, portable
co_filename = bare script name). Writes a sha256 manifest next to it.
    py -3.7 tools/build_script_archive.py build/<outdir>
"""
import hashlib, json, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import compile as compiler
assert sys.version_info[:2] == (3, 7), 'run with py -3.7'
out = ROOT / sys.argv[1]
out.mkdir(parents=True, exist_ok=True)
# compile.build walks Scripts/ recursively (ctypes/ subpackage included) and
# never deploys; the flat *.py loop used before dropped ctypes/ (found 2026-09-24).
archive_path, count = compiler.build(str(out), release=False)
archive = Path(archive_path)
sources = sorted(p for p in (ROOT / 'Scripts').rglob('*.py') if '__pycache__' not in p.parts)
assert count == len(sources), (count, len(sources))
with zipfile.ZipFile(str(archive)) as zf:
    assert {'ctypes/__init__.pyc', 'ctypes/_endian.pyc'} <= set(zf.namelist()), 'ctypes/ subpackage missing from archive'
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
manifest = {'archive': archive.relative_to(ROOT).as_posix(), 'bytes': archive.stat().st_size, 'sha256': digest,
            'modules': len(sources),
            'sources': {s.relative_to(ROOT / 'Scripts').as_posix(): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}}
(out / 'script-manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
print('archive', archive, archive.stat().st_size, 'bytes', len(sources), 'modules sha', digest[:16])
