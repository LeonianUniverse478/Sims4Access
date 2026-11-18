"""Offline checks of contribution scope, focus, wall anchor and bridge contracts."""
import ast
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'Scripts'

def functions(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=selected), filename, 'exec'), namespace)

def entry(ident, category='chairs', distance=8, sim=False, level=0):
    return types.SimpleNamespace(obj_id=ident, category=category, distance=distance,
                                 is_sim=sim, level_delta=level)

scope = ['6 meters', 6, 'distance']
ns = {'_range': lambda: scope, '_object_for_entry': lambda e: objects.get(e.obj_id),
      '_on_active_lot': lambda o: o.on_lot, '_room_id': lambda o: o.room}
functions('tyjokr_a11y_scanner.py', {'_in_range'}, ns)
assert ns['_in_range'](entry(1, distance=80, sim=True), None)
assert not ns['_in_range'](entry(2, distance=8), None)
objects = {1: types.SimpleNamespace(on_lot=True, room=7),
           2: types.SimpleNamespace(on_lot=False, room=7)}
scope[:] = ['whole lot', None, 'lot']
assert ns['_in_range'](entry(1, distance=80), None)
assert not ns['_in_range'](entry(2), None)
scope[:] = ['this room', None, 'room']
assert ns['_in_range'](entry(1), 7)
assert not ns['_in_range'](entry(1, level=1), 7)
assert not ns['_in_range'](entry(1), None)
grid = types.ModuleType('tyjokr_a11y_grid'); grid._tile=(2,3); grid._facing=0; grid._level=0
tiles = types.ModuleType('tyjokr_a11y_tiles'); tiles.STEPS=((0,1),(1,0),(0,-1),(-1,0))
tiles.position=lambda *a: types.SimpleNamespace(x=12.,y=5.,z=23.)
sys.modules[grid.__name__]=grid; sys.modules[tiles.__name__]=tiles
mathmod = types.ModuleType('sims4.math'); mathmod.Vector3=lambda x,y,z: (x,y,z)
sims4=types.ModuleType('sims4'); sims4.math=mathmod
sys.modules['sims4']=sims4; sys.modules['sims4.math']=mathmod
frame=types.SimpleNamespace(world=lambda i,j:(10.+i,20.+j), yaw=lambda side:side)
w={'_wall_state':lambda:(frame,{0:'wall'},{}), 'selected_height':lambda:('middle',1.5)}
w.update({'_blocked':lambda side:side in ('wall','blocked'),'separates_rooms':lambda frame,side:True})
functions('tyjokr_a11y_wall.py', {'selected_wall','_wall_anchor'}, w)
assert w['selected_wall']() == (frame,0)
point, height = w['_wall_anchor'](frame,0)
assert point == (12.,6.5,23.5) and height == 1.5
w['_wall_state']=lambda:(frame,{0:'wall'},{0:object()})
assert w['selected_wall']() is None
w['_wall_state']=lambda:(frame,{0:'open'},{})
assert w['selected_wall']() is None
print('1 scanner wall scenario checks passed: scopes, category identity, wall anchoring and door exclusion')
