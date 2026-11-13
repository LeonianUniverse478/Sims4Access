"""Disassemble EA game Python modules for reading (no decompiler needed).

    py -3.7 tools/rebase/ea_dis.py <out_dir> holidays/holiday_service drama_scheduler/drama_scheduler ...

Reads Data/Simulation/Gameplay/*.zip from TS4_INSTALL in dev.local.json."""
import dis, io, json, marshal, pathlib, sys, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
game = pathlib.Path(json.loads((ROOT / 'dev.local.json').read_text())['TS4_INSTALL']) / 'Data/Simulation/Gameplay'
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
zips = [zipfile.ZipFile(game / z) for z in ('base.zip', 'core.zip', 'simulation.zip')]
for name in sys.argv[2:]:
    member = name + '.pyc'
    for z in zips:
        if member in z.namelist():
            code = marshal.loads(z.read(member)[16:])
            buf = io.StringIO()
            dis.dis(code, file=buf)
            (out / (name.replace('/', '.') + '.dis')).write_text(buf.getvalue(), encoding='utf-8')
            print('ok', name)
            break
    else:
        print('missing', name)
