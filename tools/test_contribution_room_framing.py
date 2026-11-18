"""Check fixed-target camera widening and guarded room drawing offline."""
import ast
import pathlib
import sys
import types

source = pathlib.Path(__file__).resolve().parents[1] / 'Scripts/tyjokr_a11y_house_planner.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('_room_overview', 'overview_point_and_act')]
calls = []
camera = types.ModuleType('camera')
camera.focus_on_object_from_position = lambda **kw: calls.append(kw)
terrain = types.ModuleType('terrain'); terrain.get_terrain_height = lambda x,z: 0
mathmod = types.ModuleType('sims4.math'); mathmod.Vector3 = lambda *v: v
sims4 = types.ModuleType('sims4'); sims4.math = mathmod
sys.modules.update({'camera':camera, 'terrain':terrain, 'sims4':sims4, 'sims4.math':mathmod})
ns = {'time':types.SimpleNamespace(sleep=lambda seconds:None), '_log':lambda text:None}
exec(compile(ast.Module(body=nodes), str(source), 'exec'), ns)
points = ((100.,200.),(110.,210.))
for attempt in range(5): ns['_room_overview'](points,0,attempt)
assert len(set(c['obj_position'] for c in calls)) == 1
assert all(calls[i]['camera_position'][1] < calls[i+1]['camera_position'][1] for i in range(4))
build = types.ModuleType('tyjokr_a11y_plus_build')
build._hook_replies = build.cursor_off = build.park_mouse = lambda:None
build.on_main = lambda fn,*args:fn(*args)
build.project = lambda *a,**kw:(500,900)
build._clear_of_panels = lambda p:False
build._stage_size = lambda:(1920,1080)
build.core = types.SimpleNamespace(post=lambda *a:None, speak=lambda *a:None)
sys.modules[build.__name__] = build
actions=[]
assert ns['overview_point_and_act'](points,0,actions.append,'room',overview=True) is False
assert actions == []
build._clear_of_panels = lambda p:True
assert ns['overview_point_and_act'](points,0,actions.append,'room',overview=True) is True
assert len(actions) == 1
ns['_original_point_and_act'] = lambda *a,**kw:'baseline'
assert ns['overview_point_and_act'](points,0,actions.append,'door') == 'baseline'
print('1 room framing scenario checks passed: target, camera distance, guarded drawing and delegation')
