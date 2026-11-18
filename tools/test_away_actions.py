"""Native household portrait routing and stale away-action picker guards."""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
speech=types.SimpleNamespace(speak=Mock(),log_line=Mock())
services=types.SimpleNamespace()
place=types.SimpleNamespace(in_build_mode=lambda:False)
scanner=types.SimpleNamespace(_send_ui=Mock(return_value=True))
hub=types.SimpleNamespace(_window=Mock(return_value=True))
sys.modules.update(tyjokr_a11y_speech=speech,tyjokr_a11y_lang=types.SimpleNamespace(t=lambda s:s),
 services=services,tyjokr_a11y_place=place,tyjokr_a11y_scanner=scanner,
 tyjokr_a11y_hub=hub,tyjokr_a11y_menu=types.SimpleNamespace(_raw=lambda s:s))
sys.modules['server.pick_info']=types.SimpleNamespace(PickType=types.SimpleNamespace(PICK_SKEWER=11))
spec=importlib.util.spec_from_file_location('away',str(ROOT/'Scripts/tyjokr_a11y_away.py'))
away=importlib.util.module_from_spec(spec);spec.loader.exec_module(away)


class AwayTests(unittest.TestCase):
 def setUp(self):
  speech.speak.reset_mock();speech.log_line.reset_mock();scanner._send_ui.reset_mock(return_value=True)
  hub._window.reset_mock(return_value=True);place.in_build_mode=lambda:False
  self.household=types.SimpleNamespace(id=8)
  self.actor_info=self.info(1,'Active',True)
  self.actor=types.SimpleNamespace(sim_info=self.actor_info,position=types.SimpleNamespace(x=1.5,y=3,z=-4),level=2)
  self.remote=self.info(18446744073709551615,'Home|Sim')
  self.local=self.info(3,'Local',True);self.baby=self.info(4,'Baby');self.baby.is_baby=True
  self.infos=[self.actor_info,self.remote,self.local,self.baby]
  self.household.sim_info_gen=lambda:iter(self.infos)
  self.lot=types.SimpleNamespace(lot_id=77)
  services.get_active_sim=lambda:self.actor;services.active_household=lambda:self.household
  services.active_lot=lambda:self.lot;services.current_zone_id=lambda:99
 def info(self,ident,name,instanced=False):
  return types.SimpleNamespace(sim_id=ident,first_name=name,last_name='',household=self.household,
   is_baby=False,get_sim_instance=lambda:object() if instanced else None)
 def choose(self):return away.open_sim(self.remote.sim_id,1,99,8)
 def test_picker_lists_only_remote_nonbaby_household_sims(self):
  self.assertTrue(away.open_away_actions());args=hub._window.call_args[0]
  self.assertEqual(args[:2],('away actions','away actions instructions'))
  self.assertEqual([r[0] for r in args[2]],['Home|Sim']);scanner._send_ui.assert_not_called()
 def test_selection_opens_native_skewer_menu_without_switching_actor(self):
  self.assertTrue(away.open_away_actions());hub._window.call_args[0][2][0][2]()
  self.assertEqual(scanner._send_ui.call_args[0][0],
   'A11y|pick|18446744073709551615|11|77|Home Sim|1.500|3.000|-4.000|2')
  self.assertIs(services.get_active_sim(),self.actor)
 def test_returned_sim_is_refused_on_selection(self):
  self.remote.get_sim_instance=lambda:object();self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_removed_household_member_is_refused(self):
  self.infos.remove(self.remote);self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_actor_change_is_refused(self):
  self.actor.sim_info=self.local;self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_zone_change_is_refused(self):
  services.current_zone_id=lambda:100;self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_household_change_is_refused(self):
  self.household.id=9;self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_build_mode_is_refused(self):
  place.in_build_mode=lambda:True;self.assertFalse(away.open_away_actions());self.assertFalse(self.choose())
  scanner._send_ui.assert_not_called()
 def test_no_actor_or_lot_is_refused(self):
  services.get_active_sim=lambda:None;self.assertFalse(away.open_away_actions())
  services.get_active_sim=lambda:self.actor;services.active_lot=lambda:None;self.assertFalse(self.choose())
 def test_empty_list_has_feedback_and_no_picker(self):
  self.infos.remove(self.remote);self.assertFalse(away.open_away_actions());hub._window.assert_not_called()
  speech.speak.assert_called_with('no away household sims',explicit=True)
 def test_invalid_coordinates_are_refused(self):
  self.actor.position.x=float('nan');self.assertFalse(self.choose());scanner._send_ui.assert_not_called()
 def test_wide_lot_id_uses_current_lot_sentinel(self):
  self.lot.lot_id=2**50;self.assertTrue(self.choose());self.assertIn('|11|0|',scanner._send_ui.call_args[0][0])
 def test_send_failure_is_announced_and_logged(self):
  scanner._send_ui.return_value=False;self.assertFalse(self.choose())
  speech.speak.assert_called_with('action unavailable',explicit=True);self.assertTrue(speech.log_line.called)
 def test_native_failures_are_contained(self):
  scanner._send_ui.side_effect=RuntimeError('transport failed')
  try:self.assertFalse(self.choose())
  finally:scanner._send_ui.side_effect=None
 def test_hub_has_one_row_lazy_callback_and_console_command(self):
  tree=ast.parse((ROOT/'Scripts/tyjokr_a11y_hub.py').read_text(encoding='utf-8-sig'))
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='away_actions')
  module=types.SimpleNamespace(open_away_actions=Mock(return_value=True))
  sys.modules['tyjokr_a11y_away']=module
  namespace={};exec(compile(ast.Module(body=[fn]),'<hub callback>','exec'),namespace)
  self.assertTrue(namespace['away_actions']());module.open_away_actions.assert_called_once_with()
  source=(ROOT/'Scripts/tyjokr_a11y_hub.py').read_text(encoding='utf-8-sig')
  self.assertEqual(source.count("('away actions', away_actions)"),1)
  self.assertIn("Command('a11y.away'",source)

if __name__=='__main__':unittest.main()
