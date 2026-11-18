import pathlib
"""Native floor-key ownership and current Build-menu routing, without game input."""
import contextlib,pathlib,sys,types,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'Scripts'))
import tyjokr_a11y_build_helpers as h
class Tests(unittest.TestCase):
 def setUp(self):
  self.floor=0;self.events=[];self.released=False;self.geometry=(1,0,0,1920,1080,96);self.modifier=False;self.stall=False
  self.state={'zone':1,'floor':0,'center':(10,20),'grid':True,'owner':True}
  self.build=types.SimpleNamespace(current_floor=lambda:self.floor,on_main=lambda fn,*args:fn(*args))
  self.u=types.SimpleNamespace(GetAsyncKeyState=lambda k:0x8000 if self.modifier and k==17 else 0,keybd_event=self.key)
  @contextlib.contextmanager
  def physical(u):
   self.events.append('physical-on')
   try:yield
   finally:self.events.append('physical-restored')
  def measure(*args):self.events.append('roundtrip');self.released=True
  self.coords=types.SimpleNamespace(_api=lambda:self.u,physical_context=physical,window=lambda u:self.geometry,_measure=measure)
  h._build,h._coordinates=self.build,self.coords
  self.patches=[patch.object(h,'_native_floor',side_effect=lambda state:{'floor':self.floor,'minimum':-4,'maximum':4}),patch.object(h,'_state',side_effect=lambda:dict(self.state)),patch.object(h,'_same_world',return_value=True),patch.object(h,'_grid_message',side_effect=self.events.append),patch.object(h,'_grid_released',side_effect=lambda:self.released),patch.object(h,'_restore_grid',side_effect=lambda state:self.events.append('restore-grid') or True),patch.object(h,'_log'),patch.object(h.time,'sleep',return_value=None)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def key(self,key,scan,flags,extra):
  self.events.append(('key',key,scan,flags))
  if flags==3 and not self.stall:self.floor += 1 if key==33 else -1
 def test_grid_releases_before_native_key_and_is_restored(self):
  self.assertTrue(h.set_floor(1));self.assertEqual(self.floor,1)
  self.assertLess(self.events.index('A11yBuildGridOff'),self.events.index('roundtrip'))
  self.assertLess(self.events.index('roundtrip'),self.events.index(('key',33,0x49,1)))
  self.assertEqual(self.events[-1],'restore-grid');self.assertIn('physical-restored',self.events)
 def test_downward_and_multiple_levels_follow_native_report(self):
  self.floor=2;self.state['floor']=2
  self.assertTrue(h.set_floor(-1));self.assertEqual(self.floor,-1)
  self.assertEqual(len([x for x in self.events if isinstance(x,tuple) and x[-1]==1]),3)
 def test_already_on_floor_emits_no_input_or_grid_messages(self):
  self.assertTrue(h.set_floor(0));self.assertEqual(self.events,[])
 def test_inactive_grid_is_not_reenabled(self):
  self.state.update(grid=False,owner=False);self.released=True
  self.assertTrue(h.set_floor(1));self.assertNotIn('restore-grid',self.events);self.assertNotIn('A11yBuildGridOff',self.events)
 def test_no_key_before_native_ack(self):
  self.coords._measure=lambda *a:self.events.append('roundtrip')
  with patch.object(h.time,'monotonic',side_effect=[0,3]):self.assertFalse(h.set_floor(1))
  self.assertFalse(any(isinstance(x,tuple) for x in self.events));self.assertIn('restore-grid',self.events)
 def test_native_context_change_refuses_input(self):
  h._same_world.return_value=False
  self.assertFalse(h.set_floor(1));self.assertFalse(any(isinstance(x,tuple) for x in self.events))
 def test_modifier_keys_are_never_borrowed(self):
  self.modifier=True;self.assertFalse(h.set_floor(1));self.assertFalse(any(isinstance(x,tuple) for x in self.events))
 def test_floor_boundary_stops_without_repeating_unacknowledged_key(self):
  self.stall=True;self.assertFalse(h.set_floor(1))
  self.assertEqual(len([x for x in self.events if isinstance(x,tuple) and x[-1]==1]),1)
 def test_key_up_survives_failure_after_key_down(self):
  h.time.sleep.side_effect=RuntimeError('interrupted')
  self.assertFalse(h.set_floor(1));self.assertIn(('key',33,0x49,3),self.events);self.assertIn('restore-grid',self.events)
 def test_invalid_floor_requests_are_safe(self):
  for value in [True,1.5,float('nan'),float('inf'),10**1000,'1',None]:self.assertFalse(h.set_floor(value))
  self.assertEqual(self.events,[])
 def test_alt_b_is_the_engines_own_menu(self):
  # Merged 2026-11-14: one registration, no later rebinding by helper modules.
  scripts=pathlib.Path(__file__).resolve().parents[1]/'Scripts'
  self.assertEqual((scripts/'tyjokr_a11y_plus_build.py').read_text(encoding='utf-8').count('@core.hotkey(ord("B")'),1)
  for path in scripts.glob('tyjokr_a11y_*.py'):
   if not path.name.startswith('tyjokr_a11y_plus'):self.assertNotIn('HOTKEYS[',path.read_text(encoding='utf-8'),path.name)
 def test_camera_estimate_cannot_override_native_floor(self):
  self.state['floor']=-1
  self.assertTrue(h.set_floor(0));self.assertEqual(self.events,[])
 def test_out_of_native_bounds_never_sends_input(self):
  h._native_floor.side_effect=lambda state:{'floor':0,'minimum':0,'maximum':3}
  self.assertFalse(h.set_floor(-1));self.assertEqual(self.events,[])
 def test_unexpected_native_jump_stops_before_another_key(self):
  original=self.u.keybd_event
  def jump(key,scan,flags,extra):
   original(key,scan,flags,extra)
   if flags==3:self.floor=2
  self.u.keybd_event=jump
  self.assertFalse(h.set_floor(1))
  self.assertEqual(len([x for x in self.events if isinstance(x,tuple) and x[-1]==1]),1)
 def test_stair_plan_cleanup_after_early_failure(self):
  planner=types.SimpleNamespace(_pending_stairs=['stale basement'])
  plan=types.SimpleNamespace(_a11y_transitions=[('new',0,1)])
  def fail(p):
   self.assertEqual(h._house_context.transitions,tuple(plan._a11y_transitions))
   raise RuntimeError('room failed')
  with patch.object(h,'_planner',planner),patch.object(h,'_original_house_build',side_effect=fail):
   with self.assertRaises(RuntimeError):h._house_build(plan)
  self.assertEqual(planner._pending_stairs,[])
 def test_ordinary_house_discards_abandoned_basement_stairs(self):
  planner=types.SimpleNamespace(_pending_stairs=['basement'])
  with patch.object(h,'_planner',planner),patch.object(h,'_original_house_build',side_effect=lambda p:self.assertEqual(planner._pending_stairs,[])):
   h._house_build(types.SimpleNamespace())
  self.assertEqual(planner._pending_stairs,[])

class TransportTests(unittest.TestCase):
 def setUp(self):
  h._floor_job=None;h._floor_sequence=-1;h._floor_quarantined=False
  h._build=types.SimpleNamespace(on_main=lambda fn,*args:fn(*args),_send_ui=lambda msg:h._receive_floor('9',1,'ok',1,-2,4))
  self.guard=patch.object(h,'_same_world',return_value=True);self.guard.start();self.addCleanup(self.guard.stop)
 def tearDown(self):
  h._floor_job=None;h._floor_sequence=-1;h._floor_quarantined=False
 def test_query_accepts_authoritative_snapshot(self):
  self.assertEqual(h._native_floor({'zone':9}),{'floor':1,'minimum':-2,'maximum':4})
 def test_timeout_quarantines_channel_and_ignores_late_reply(self):
  h._build._send_ui=Mock()
  with self.assertRaises(RuntimeError):h._native_floor({'zone':9},timeout=0)
  self.assertTrue(h._floor_quarantined)
  h._receive_floor('9',1,'ok',0,-2,4)
  with self.assertRaises(RuntimeError):h._native_floor({'zone':9},timeout=0)
  self.assertEqual(h._build._send_ui.call_count,1)
 def test_wrong_zone_and_old_sequence_cannot_complete_request(self):
  h._floor_sequence=5
  def reply(msg):
   h._receive_floor('8',6,'ok',0,-2,4);self.assertFalse(h._floor_job['done'].is_set())
   h._receive_floor('9',5,'ok',0,-2,4);self.assertFalse(h._floor_job['done'].is_set())
   h._receive_floor('9',6,'ok',2,-2,4)
  h._build._send_ui=reply
  self.assertEqual(h._native_floor({'zone':9})['floor'],2)
 def test_invalid_bounds_and_native_refusal_never_become_floor_zero(self):
  for status,current,low,high in [('ok',2,3,4),('ok',False,-2,4),('unavailable',0,0,0)]:
   h._floor_sequence=-1
   h._build._send_ui=lambda msg:h._receive_floor('9',1,status,current,low,high)
   with self.assertRaises(RuntimeError):h._native_floor({'zone':9})
 def test_overlapping_query_is_refused(self):
  h._floor_lock.acquire()
  try:
   with self.assertRaises(RuntimeError):h._native_floor({'zone':9})
  finally:h._floor_lock.release()
 def test_plan_stairs_use_thread_local_plan_not_global_pending(self):
  planner=types.SimpleNamespace(_pending_stairs=['stale'],_original_stairs=Mock(return_value=True),_place_stair_at=Mock(return_value=True))
  h._house_context.transitions=(((3,4),(1,0),0,1),)
  with patch.object(h,'_planner',planner),patch.object(h,'_original_house_stairs',planner._original_stairs),patch.object(h,'_log'):
   self.assertTrue(h._stairs_for_plan((0,0),(0,1)))
   planner._place_stair_at.assert_called_once_with((3,4),(1,0),0)
   planner._original_stairs.assert_not_called()
   h._house_context.transitions=()
   self.assertTrue(h._stairs_for_plan((0,0),(0,1)))
   planner._original_stairs.assert_called_once_with((0,0),(0,1))
if __name__=='__main__':unittest.main()
