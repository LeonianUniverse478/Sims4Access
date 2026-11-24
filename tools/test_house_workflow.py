import pathlib
"""Unified planning, native geometry preservation, and cached-floor regression."""
import ast,copy,pathlib,sys,threading,types,unittest
from unittest.mock import Mock,patch
import test_scanner_v5 as env
import tyjokr_a11y_plus_build as native_build
import tyjokr_a11y_plus_house as native_house
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'Scripts'))
import tyjokr_a11y_house_workflow as w
ROOT=pathlib.Path(__file__).resolve().parents[1]
# Execute the existing plan generator without its import-time integration hooks.
tree=ast.parse((ROOT/'Scripts/tyjokr_a11y_house_planner.py').read_text())
subset=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_room','_build_plan')])
namespace={};exec(compile(subset,'existing_house_planner','exec'),namespace)

class PlanningTests(unittest.TestCase):
 def setUp(self):
  self.menus=[];self.text=[]
  frame=types.SimpleNamespace(width=40,depth=40)
  self.frame=frame
  core=types.SimpleNamespace(choose=lambda *a,**k:self.menus.append((a,k)),speak=Mock(),ask_text=lambda *a:self.text.append(a))
  planner=types.SimpleNamespace(_limits=lambda:(-4,3),_build_plan=namespace['_build_plan'])
  self.patches=[patch.object(native_build,'frame',return_value=frame),patch.object(native_house,'street_side',return_value='north'),patch.object(w,'_build',native_build),patch.object(w,'_house',native_house),patch.object(w,'_planner',planner),patch.object(w,'_core',core),patch.object(w,'_valid',return_value=True),patch.object(w,'_context',side_effect=lambda p:p),patch.object(w,'_log'),patch.object(native_build,'funds',return_value=100000),patch.object(native_build,'in_build_mode',return_value=True)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def plan(self):return native_house.make_two_floor_plan('2bed')
 def select(self,value):self.menus[-1][0][3](value)
 def test_original_two_floor_presets_keep_geometry_in_all_compass_orientations(self):
  for side in ('north','east','south','west'):
   native_house.street_side.return_value=side
   for variant in ('2bed','3bed','4bed'):
    original=native_house.make_two_floor_plan(variant);new=w._extend(original,2,False)
    self.assertEqual([(r['box'],r['uv'],r['level'],r['kind']) for r in new.rooms],[(r['box'],r['uv'],r['level'],r['kind']) for r in original.rooms])
    self.assertEqual([(d['tile_a'],d['tile_b'],d['level'],d['front']) for d in new.doors],[(d['tile_a'],d['tile_b'],d['level'],d['front']) for d in original.doors])
    self.assertEqual(new.stairs,original.stairs);self.assertEqual(len(new._a11y_transitions),1)
 def test_one_floor_preset_has_no_stairs_or_implicit_extra_floor(self):
  original=native_house.make_plan(list(native_house.PRESETS[0][1]));new=w._extend(original,1,False)
  self.assertEqual([r['box'] for r in new.rooms],[r['box'] for r in original.rooms]);self.assertIsNone(new.stairs);self.assertEqual(new._a11y_transitions,[])
 def test_extra_floors_repeat_top_layout_and_basement_uses_ground(self):
  original=self.plan();new=w._extend(original,4,True)
  for level in (-1,0,1,2,3):
   source=0 if level<=0 else 1
   self.assertEqual([r['box'] for r in new.rooms if r['level']==level],[r['box'] for r in original.rooms if r['level']==source])
  self.assertEqual([a[2:] for a in new._a11y_transitions],[(-1,0),(0,1),(1,2),(2,3)])
  self.assertEqual(sum(d['front'] for d in new.doors),1)
 def test_changing_story_count_preserves_existing_basement_custom_names(self):
  plan=w._extend(self.plan(),2,True);plan.rooms[0]['name']='Hobby basement';plan.rooms[0]['kind']='room'
  changed=w._extend(plan,3,True)
  self.assertEqual(changed.rooms[0]['name'],'Hobby basement');self.assertEqual(changed.rooms[0]['kind'],'room')
 def test_repeated_extensions_do_not_accumulate_floor_prefixes(self):
  plan=w._extend(self.plan(),3,False);new=w._extend(plan,4,False)
  self.assertTrue(all('Floor 3' not in r['name'] for r in new.rooms if r['level']==3))
 def test_removing_stories_removes_their_doors_and_stairs(self):
  plan=w._extend(self.plan(),3,True);new=w._extend(plan,1,False)
  self.assertTrue(all(r['level']==0 for r in new.rooms));self.assertTrue(all(d['level']==0 for d in new.doors));self.assertIsNone(new.stairs)
 def test_unverified_story_counts_and_missing_stair_hallway_are_refused(self):
  for count in (0,5,True,1.5):
   with self.assertRaises(ValueError):w._extend(self.plan(),count,False)
  plan=self.plan();plan.rooms=[r for r in plan.rooms if r['kind']!='hall']
  with self.assertRaises(ValueError):w._extend(plan,2,False)
 def test_both_custom_layouts_produce_the_expected_rooms_on_every_floor(self):
  for layout,count in [('two',2),('four',4)]:
   base=namespace['_build_plan'](10,10,[0],layout,{0:['Room {}'.format(i) for i in range(count)]})
   plan=w._extend(base,3,True)
   for level in (-1,0,1,2):
    self.assertEqual(sum(r['level']==level and r['kind']!='hall' for r in plan.rooms),count)
   self.assertEqual(len(plan._a11y_transitions),3)
 def test_renaming_a_room_updates_connected_door_labels_without_moving_them(self):
  plan=self.plan();geometry=copy.deepcopy([(d['tile_a'],d['tile_b']) for d in plan.doors]);plan.rooms[0]['name']='Family lounge';w._door_names(plan)
  self.assertTrue(any('Family lounge' in d['what'] for d in plan.doors));self.assertEqual([(d['tile_a'],d['tile_b']) for d in plan.doors],geometry)
 def test_actual_compass_description_rotates_with_the_existing_plan_mapping(self):
  native_house.street_side.return_value='west';plan=self.plan();text=w._position(plan,plan.rooms[0])
  self.assertIn('street-facing',text);self.assertIn('south west side',text)
 def test_unified_menu_contains_one_builder_and_preserves_other_actions(self):
  # Merged 2026-11-14 (Leo): her workflow replaces Michael Maslo's Build my
  # house, roof and lot description; his other Build helper actions stay.
  text=(pathlib.Path(__file__).resolve().parents[1]/'Scripts'/'tyjokr_a11y_plus_build.py').read_text(encoding='utf-8')
  menu=text[text.index('def open_menu():'):]
  self.assertEqual(menu.count('("Build my house"'),1);self.assertIn('workflow.open_builder',menu)
  for gone in ('("Configurable stacked house"','("Put a roof on my house"','("Describe the lot",'):self.assertNotIn(gone,menu)
  for kept in ('Door between two rooms','Furnish a room with the basics','Decorate a room','Paint the walls of a room','Undo the last build step'):self.assertIn(kept,menu)
 def test_room_editor_asks_for_one_room_instead_of_comma_separated_names(self):
  plan=self.plan();w._edit_rooms(plan);self.select(0);self.select('custom')
  self.assertEqual(len(self.text),1);self.text[0][3]('  Family   lounge  ')
  self.assertEqual(plan.rooms[0]['name'],'Family lounge');self.assertIn('Rooms and positions',self.menus[-1][0][0])
 def test_role_selection_keeps_room_geometry(self):
  plan=self.plan();box=plan.rooms[0]['box'];w._edit_rooms(plan);self.select(0);self.select(("Children's bedroom",'bedroom'))
  self.assertEqual(plan.rooms[0]['name'],"Children's bedroom");self.assertEqual(plan.rooms[0]['box'],box)
 def test_review_does_not_build_until_explicit_confirmation_and_rechecks_context(self):
  plan=w._extend(self.plan(),2,False)
  with patch.object(native_house,'start_build') as start:
   w._review(plan);start.assert_not_called();w._valid.return_value=False;self.select('build');start.assert_not_called()
 def test_review_uses_the_existing_construction_entry_and_plan_stair_scope(self):
  plan=w._extend(self.plan(),2,True)
  with patch.object(native_house,'start_build') as start:
   w._review(plan);self.select('build');start.assert_called_once_with(plan)
   self.assertTrue(plan._a11y_roof_prompt);self.assertEqual(len(plan._a11y_transitions),2)
 def test_ready_made_list_keeps_all_original_presets(self):
  w._ready_made();rows=self.menus[-1][0][2]
  self.assertEqual(len(rows),len(native_house.PRESETS)+len(native_house.TWO_FLOOR_PRESETS))

class ScanTests(unittest.TestCase):
 def setUp(self):
  self.active=False;self.events=[]
  class Lot:
   _min_level=0;_max_level=0
   @property
   def min_level(s):
    if s._min_level is None:s._min_level=-1
    return s._min_level
   @property
   def max_level(s):
    if s._max_level is None:s._max_level=2
    return s._max_level
   def clear_cached_level_range(s):s._min_level=s._max_level=None
  self.lot=Lot();self.native=lambda:[self.lot.min_level,self.lot.max_level]
  self.patches=[patch.dict(sys.modules,services=types.SimpleNamespace(active_lot=lambda:self.lot)),patch.object(w,'_build',types.SimpleNamespace(in_build_mode=lambda:self.active,on_main=lambda fn:fn())),patch.object(w,'_original_scan',side_effect=self.native),patch.object(w,'_main_ident',threading.get_ident()),patch.object(w,'_log')]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def test_empty_lot_cached_zero_range_cannot_hide_new_basement_or_upper_story(self):
  self.assertEqual(self.native(),[0,0]);self.active=True;self.assertEqual(w._scan_rooms(),[-1,2])
 def test_live_mode_keeps_the_original_cache_behavior(self):self.assertEqual(w._scan_rooms(),[0,0])
 def test_worker_scan_is_marshalled_without_calling_game_apis_on_worker(self):
  self.active=True
  with patch.object(w,'_main_ident',-1):
   w._build.on_main=Mock(return_value=['pumped']);self.assertEqual(w._scan_rooms(),['pumped'])
   w._original_scan.assert_not_called();self.assertEqual(self.lot._min_level,0)
 def test_timeout_never_returns_an_empty_geometry_as_success(self):
  with patch.object(w,'_main_ident',-1):
   w._build.on_main=lambda fn:None
   with self.assertRaises(RuntimeError):w._scan_rooms()
 def test_uninitialised_thread_guard_never_runs_native_scan(self):
  with patch.object(w,'_main_ident',None):
   with self.assertRaises(RuntimeError):w._scan_rooms()
  w._original_scan.assert_not_called()
 def test_basement_failure_message_does_not_claim_wrong_room_size(self):
  basement=types.SimpleNamespace(failure_reason=lambda:'the basement room was not verified')
  with patch.dict(sys.modules,tyjokr_a11y_basement=basement),patch.object(w,'_original_say') as say:
   w._say('I stopped building at the storage room, because it came out a different size.')
   self.assertIn('basement room was not verified',say.call_args[0][0]);self.assertNotIn('different size',say.call_args[0][0])
   w._say('Building the living room.');say.assert_called_with('Building the living room.')

if __name__=='__main__':unittest.main()
