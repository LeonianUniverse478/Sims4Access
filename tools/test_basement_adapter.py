"""Basement adapter safety and wiring, without native input or purchases."""
import contextlib,pathlib,sys,tempfile,types,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'Scripts'))
import tyjokr_a11y_basement as b

class DrawTests(unittest.TestCase):
 def setUp(self):
  self.box=(2,3,6,8);self.state={'zone':9,'household':1};self.before={((12,12,14,14),0)};self.after=self.before|{(self.box,-1)}
  self.frame=types.SimpleNamespace(width=20,depth=20,world=lambda x,z:(100+x,200-z))
  self.build=types.SimpleNamespace(on_main=lambda fn,*a:fn(*a),frame=lambda:self.frame,set_floor=Mock(return_value=True),drag=Mock(),_last_error={'text':'old message','at':-1},_busy=[False],funds=lambda:10000)
  def point(points,level,action,description,**kwargs):action([(10,20),(30,40)]);return True
  self.build.point_and_act=Mock(side_effect=point)
  b._build=self.build;b._core=types.SimpleNamespace(post=lambda fn,*a:fn(*a),speak=Mock(),log_exc=Mock())
  b._helpers=types.SimpleNamespace(_native_floor=Mock(return_value={'floor':0,'minimum':-4,'maximum':4}))
  self.patches=[patch.object(b,'_context',return_value=self.state),patch.object(b,'_same_context',return_value=True),patch.object(b,'_rooms',side_effect=lambda:self.after if self.build.drag.called else self.before),patch.object(b,'_rectangle',return_value=True),patch.object(b,'_tool',return_value=True),patch.object(b,'_log'),patch.object(b,'_enabled',return_value=True),patch.object(b.time,'sleep',return_value=None)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def test_basement_draws_from_ground_and_verifies_negative_floor(self):
  self.assertEqual(b._draw(self.box,True),self.box)
  self.build.set_floor.assert_called_once_with(0)
  args=self.build.point_and_act.call_args
  self.assertEqual(args[0][0],[(102,197),(106,192)]);self.assertEqual(args[0][1],0)
  self.assertTrue(args[1]['overview']);self.build.drag.assert_called_once_with((10,20),(30,40))
  self.assertEqual([c[0][0] for c in b._tool.call_args_list],[b.TOOL,b.TOOL,'Room Tool'])
 def test_original_room_worker_is_preserved_on_other_levels(self):
  with patch.object(b,'_original_room',return_value='ordinary') as original:
   for level in (0,1,2,-2):
    self.assertEqual(b.room_worker(self.box,overview=True,tries=2,level=level),'ordinary')
    original.assert_called_with(self.box,overview=True,tries=2,level=level)
  self.build.drag.assert_not_called()
 def test_disabled_experimental_flag_never_draws(self):
  b._enabled.return_value=False
  self.assertEqual(b.room_worker(self.box,level=-1),'disabled');self.build.drag.assert_not_called()
 def test_out_of_bounds_is_rejected_before_floor_or_tool_input(self):
  self.assertEqual(b.room_worker((0,3,6,8),level=-1),'unverified')
  self.build.set_floor.assert_not_called();b._tool.assert_not_called()
 def test_existing_basement_overlap_is_not_modified(self):
  self.before.add(((3,4,5,7),-1))
  self.assertEqual(b._draw(self.box,True),'occupied');self.build.drag.assert_not_called()
 def test_missing_basement_tool_prevents_drag_and_restores_room_tool(self):
  b._tool.side_effect=[False,True]
  self.assertEqual(b._draw(self.box,True),'nocatalog');self.build.drag.assert_not_called()
  self.assertEqual(b._tool.call_args[0][0],'Room Tool')
 def test_unknown_native_floor_stops_before_drawing(self):
  self.build.set_floor.return_value=False
  self.assertEqual(b._draw(self.box,True),'nofloor');b._tool.assert_not_called()
 def test_changed_native_floor_refuses_the_drag(self):
  b._helpers._native_floor.return_value={'floor':1}
  self.assertEqual(b.room_worker(self.box,True,level=-1),'unverified');self.build.drag.assert_not_called()
  self.assertEqual(b._tool.call_args[0][0],'Room Tool')
 def test_wrong_level_never_counts_as_success(self):
  self.after=self.before|{(self.box,0)}
  self.assertEqual(b._draw(self.box,True),'unverified')
 def test_changed_or_missing_prior_rooms_stop_the_plan(self):
  self.after={(self.box,-1)}
  self.assertEqual(b._draw(self.box,True),'unverified')
 def test_wrong_footprint_never_counts_as_success(self):
  self.after=self.before|{((2,3,7,8),-1)}
  self.assertEqual(b._draw(self.box,True),'unverified')
 def test_holes_in_target_footprint_never_count_as_success(self):
  b._rectangle.return_value=False
  self.assertEqual(b._draw(self.box,True),'unverified')
 def test_restore_failure_prevents_the_next_room(self):
  b._tool.side_effect=[True,True,False]
  self.assertEqual(b._draw(self.box,True),'nocatalog')
 def test_context_change_prevents_drag_and_does_not_restore_into_dialog(self):
  b._same_context.return_value=False
  self.assertEqual(b.room_worker(self.box,True,level=-1),'unverified')
  self.build.drag.assert_not_called()
 def test_no_geometry_acknowledgement_does_not_repeat_purchases_or_undo(self):
  self.after=self.before
  self.assertEqual(b._draw(self.box,True),'unverified');self.assertEqual(self.build.drag.call_count,1)
 def test_adjacent_basement_rooms_are_permitted_but_not_overlaps(self):
  self.before.add(((6,3,9,8),-1));self.after=self.before|{(self.box,-1)}
  self.assertEqual(b._draw(self.box,True),self.box)

 def test_inspection_never_changes_catalog_selection_or_buys(self):
  self.build.fetch_catalog=Mock()
  def thread(target,**kwargs):return types.SimpleNamespace(start=target)
  with patch.object(b.threading,'Thread',side_effect=thread):b._inspect()
  self.build.fetch_catalog.assert_not_called();self.build.drag.assert_not_called();b._tool.assert_not_called()
  self.assertFalse(self.build._busy[0])

class DetailTests(unittest.TestCase):
 def test_bounds_reject_invalid_numbers(self):
  f=types.SimpleNamespace(width=20,depth=20)
  for value in [(1,2,3), (True,2,3,4), (1,2,float('nan'),4),(1,2,3.5,4),(4,2,3,5),(1,2,20,5)]:
   with self.assertRaises(ValueError):b._bounds(value,f)
 def test_rectangle_requires_every_tile_and_exact_level(self):
  room=types.SimpleNamespace(level=-1,tiles=[(2.5,3.5),(3.5,3.5),(2.5,4.5),(3.5,4.5)])
  frame=types.SimpleNamespace(local=lambda x,z:(x,z))
  b._build=types.SimpleNamespace(frame=lambda:frame,_room_box=lambda r:(2,3,4,5))
  native=types.SimpleNamespace(scan_rooms=lambda:[room])
  with patch.dict(sys.modules,tyjokr_a11y_plus_rooms=native):
   self.assertTrue(b._rectangle((2,3,4,5)));room.tiles.pop();self.assertFalse(b._rectangle((2,3,4,5)))
   room.level=0;self.assertFalse(b._rectangle((2,3,4,5)))
 def test_reply_delegates_and_requires_matching_native_selection(self):
  b._original_reply=Mock(return_value='original');b._build=types.SimpleNamespace(_cat={'serial':12})
  import threading
  job={'index':3,'name':'Basement Tool','serial':12,'done':threading.Event()};b._selection=job
  try:
   self.assertEqual(b.reply('selected%7C2%7CBasement%2520Tool'),'original');self.assertFalse(job['done'].is_set())
   b.reply('selected%7C3%7CRoom%2520Tool');self.assertFalse(job['done'].is_set())
   b.reply('selected%7C3%7CBasement%2520Tool');self.assertTrue(job['done'].is_set())
   self.assertEqual(b._original_reply.call_count,3)
  finally:b._selection=None
 def test_tool_requires_real_catalog_match_and_selection_ack(self):
  state={'zone':1};b._build=types.SimpleNamespace(on_main=lambda fn,*a:fn(*a),_cat={'serial':2},fetch_catalog=Mock(return_value=[('Room Tool',0,1),('Basement Tool',0,1)]))
  def select(index,name):b._selection['done'].set()
  b._build.select_item=Mock(side_effect=select)
  with patch.object(b,'_same_context',return_value=True),patch.object(b,'_log'):
   self.assertTrue(b._tool('Basement Tool',state));b._build.select_item.assert_called_once_with(1,'Basement Tool')
   b._build.select_item.reset_mock();b._build._cat['chosen']=99;self.assertFalse(b._tool('Custom Basement Tool',state));b._build.select_item.assert_not_called();self.assertNotIn('chosen',b._build._cat)
 def test_build_helper_lists_the_assistant_once(self):
  # Merged 2026-11-14: the Build helper menu names the assistant directly.
  text=(pathlib.Path(__file__).resolve().parents[1]/'Scripts'/'tyjokr_a11y_plus_build.py').read_text(encoding='utf-8')
  menu=text[text.index('def open_menu():'):]
  self.assertEqual(menu.count('basement.open_assistant'),1)
 def test_setting_is_a_normal_setting_with_the_old_line_still_read(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('settings_for_basement',str(pathlib.Path(__file__).resolve().parents[1]/'Scripts'/'tyjokr_a11y_settings.py'))
  settings=importlib.util.module_from_spec(spec);spec.loader.exec_module(settings)
  self.assertIs(settings.DEFAULTS[b.SETTING],True);self.assertIn(b.SETTING,settings._BOOL_KEYS)
  self.assertEqual(settings._FILE_MAP[('contribution','experimental basement')],b.SETTING)
  self.assertEqual(settings._FILE_MAP[('build cursor','basement')],b.SETTING)
  self.assertIn('basement = off',settings._render({b.SETTING:False}).splitlines())
  menu=(pathlib.Path(__file__).resolve().parents[1]/'Scripts'/'tyjokr_a11y_menu.py').read_text(encoding='utf-8')
  self.assertLess(menu.index("Row('experimental_basement'"),menu.index("Row('reload'"))

if __name__=='__main__':unittest.main()
