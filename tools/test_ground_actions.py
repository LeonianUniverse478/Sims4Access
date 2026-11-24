"""Native floor picks preserve story and position and never choose an action."""
import ast
import importlib.util
import pathlib
import sys
import types
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
speech=types.ModuleType('tyjokr_a11y_speech'); spoken=[]; logs=[]
speech.speak=lambda text,**kw:spoken.append(text);speech.log_line=logs.append
services=types.ModuleType('services');place=types.ModuleType('tyjokr_a11y_place')
scanner=types.ModuleType('tyjokr_a11y_scanner');picks=types.ModuleType('server.pick_info')
picks.PickType=types.SimpleNamespace(PICK_FLOOR=5)
server=types.ModuleType('server');server.pick_info=picks
routing=types.ModuleType('routing');terrain=types.ModuleType('terrain')
routing.SurfaceType=types.SimpleNamespace(SURFACETYPE_WORLD=1)
routing.SurfaceIdentifier=lambda zone,level,kind:(zone,level,kind)
sys.modules.update(routing=routing,terrain=terrain)
sys.modules.update(tyjokr_a11y_speech=speech,services=services,tyjokr_a11y_place=place,
                   tyjokr_a11y_scanner=scanner,server=server)
sys.modules['server.pick_info']=picks
spec=importlib.util.spec_from_file_location('tyjokr_a11y_ground',str(ROOT/'Scripts/tyjokr_a11y_ground.py'))
ground=importlib.util.module_from_spec(spec);spec.loader.exec_module(ground)
sys.modules['tyjokr_a11y_ground']=ground


class Tests(unittest.TestCase):
    def setUp(self):
        spoken.clear();logs.clear();self.sent=[]
        self.sim=types.SimpleNamespace(id=123,position=types.SimpleNamespace(x=10.25,y=6.5,z=-4.125),level=2)
        self.lot=types.SimpleNamespace(lot_id=77,is_position_on_lot=lambda p:True)
        services.get_active_sim=lambda:self.sim;services.active_lot=lambda:self.lot
        services.current_zone_id=lambda:999
        terrain.get_terrain_height=lambda x,z,**kw:6.5
        place.in_build_mode=lambda:False
        scanner._send_ui=lambda message:self.sent.append(message) or True
    def test_floor_pick_keeps_world_point_and_story(self):
        self.assertTrue(ground.open_floor_menu())
        self.assertEqual(self.sent,['A11y|pick|0|5|77||10.250|6.500|-4.125|2'])
    def test_basement(self):
        self.sim.level=-1;self.assertTrue(ground.open_floor_menu());self.assertTrue(self.sent[0].endswith('|-1'))
    def test_build_refuses(self):
        place.in_build_mode=lambda:True;self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_no_sim(self):
        self.sim=None;self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_no_lot(self):
        self.lot=None;self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_off_lot(self):
        self.lot.is_position_on_lot=lambda p:False
        self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_invalid_point(self):
        self.sim.position.x=float('nan');self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_invalid_lot_id(self):
        self.lot.lot_id=-1;self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_wide_lot_id_uses_native_current_lot_sentinel(self):
        self.lot.lot_id=2**40;self.assertTrue(ground.open_floor_menu())
        self.assertTrue(self.sent[0].startswith('A11y|pick|0|5|0|'))
    def test_send_failure(self):
        scanner._send_ui=lambda msg:False;self.assertFalse(ground.open_floor_menu());self.assertTrue(spoken)
    def test_floor_height_instead_of_furniture_height(self):
        self.sim.position.y=99;ground.open_floor_menu();self.assertIn('|6.500|',self.sent[0])
    def test_unavailable_floor_height_refuses(self):
        terrain.get_terrain_height=lambda *a,**kw:None
        self.assertFalse(ground.open_floor_menu());self.assertFalse(self.sent)
    def test_request_rechecks_active_sim(self):
        self.sim=types.SimpleNamespace(id=456,position=types.SimpleNamespace(x=2,y=3,z=4),level=1)
        terrain.get_terrain_height=lambda *a,**kw:3
        ground.open_floor_menu();self.assertIn('|2.000|3.000|4.000|1',self.sent[0])
    def test_hub_callback_delegates_to_native_floor_module(self):
        path=ROOT/'Scripts/tyjokr_a11y_hub.py';tree=ast.parse(path.read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='floor_interactions')
        ns={};exec(compile(ast.Module(body=[fn]),str(path),'exec'),ns)
        self.assertTrue(ns['floor_interactions']());self.assertEqual(len(self.sent),1)
        self.assertEqual(path.read_text().count("('Floor actions here', floor_interactions)"),1)


if __name__=='__main__':unittest.main()
