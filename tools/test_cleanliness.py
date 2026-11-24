"""Current native cleaning states change speech, never scanner structure."""
import ast
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
objects={};manager=types.SimpleNamespace(get=lambda ident:objects.get(ident))
speech=types.SimpleNamespace(log_line=Mock())
sys.modules.update(services=types.SimpleNamespace(object_manager=lambda:manager),
 tyjokr_a11y_lang=types.SimpleNamespace(t=lambda s:{'scanner dirty':'dirty','scanner dusty':'dusty'}.get(s,s)),
 tyjokr_a11y_speech=speech)
spec=importlib.util.spec_from_file_location('cleanliness',str(ROOT/'Scripts/tyjokr_a11y_cleanliness.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sys.modules['tyjokr_a11y_cleanliness']=module
def value(state,ident):return types.SimpleNamespace(state=types.SimpleNamespace(guid64=state),guid64=ident)

class CleaningTests(unittest.TestCase):
 def setUp(self):
  objects.clear();speech.log_line.reset_mock();module._errors_logged=0
  self.entry=types.SimpleNamespace(obj_id=5,is_sim=False)
 def set(self,*states):
  objects[5]=types.SimpleNamespace(state_component=types.SimpleNamespace(values=lambda:iter(states)))
 def test_dirty_toilet_snapshot(self):
  self.set(value(15128,15133),value(15129,15131),value(255045,255048))
  self.assertEqual(module.suffix(self.entry),', dirty')
 def test_clean_sink_snapshot(self):
  self.set(value(15128,15132),value(15129,15130),value(255045,255048))
  self.assertEqual(module.suffix(self.entry),'')
 def test_dusty_desk_is_not_dirty(self):
  self.set(value(15128,15132),value(15129,15130),value(255045,255050))
  self.assertEqual(module.suffix(self.entry),', dusty')
 def test_both_native_conditions(self):
  self.set(value(15129,15131),value(255045,255050))
  self.assertEqual(module.suffix(self.entry),', dirty, dusty')
 def test_state_is_read_again_after_cleaning(self):
  self.set(value(15129,15131));self.assertEqual(module.suffix(self.entry),', dirty')
  self.set(value(15129,15130));self.assertEqual(module.suffix(self.entry),'')
 def test_visual_clean_state_wins_over_transient_commodity_dirty(self):
  self.set(value(15129,15130),value(15128,15133));self.assertEqual(module.suffix(self.entry),'')
 def test_verified_commodity_fallback_when_visual_state_absent(self):
  self.set(value(15128,15133));self.assertEqual(module.suffix(self.entry),', dirty')
 def test_unknown_states_and_names_are_not_guessed(self):
  self.set(value(999,15131),value(15129,999),value(255045,999))
  self.assertEqual(module.suffix(self.entry),'')
 def test_missing_object_or_component(self):
  self.assertEqual(module.suffix(self.entry),'');objects[5]=object()
  self.assertEqual(module.suffix(self.entry),'')
 def test_sims_never_access_object_manager(self):
  self.entry.is_sim=True;self.assertEqual(module.suffix(self.entry),'')
 def test_read_errors_do_not_break_navigation_and_logs_are_bounded(self):
  objects[5]=types.SimpleNamespace(state_component=types.SimpleNamespace(values=Mock(side_effect=ValueError)))
  for _ in range(10):self.assertEqual(module.suffix(self.entry),'')
  self.assertEqual(speech.log_line.call_count,5)
 def test_state_iteration_is_bounded(self):
  seen=[]
  def states():
   for i in range(1000):seen.append(i);yield value(999,i)
  objects[5]=types.SimpleNamespace(state_component=types.SimpleNamespace(values=states))
  self.assertEqual(module.suffix(self.entry),'');self.assertEqual(len(seen),64)
 def production(self,name,namespace):
  tree=ast.parse((ROOT/'Scripts/tyjokr_a11y_scanner.py').read_text(encoding='utf-8-sig'))
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
  exec(compile(ast.Module(body=[fn]),'<scanner announcement>','exec'),namespace)
  return namespace[name]
 def test_scanner_preserves_localized_name_availability_and_place(self):
  self.set(value(15129,15131));self.entry.availability='locked';self.entry.role=''
  ns={'lang':sys.modules['tyjokr_a11y_lang'],'_name_part':lambda e:('loc',123),'_place_part':lambda e:'here'}
  parts=self.production('_entry_parts',ns)(self.entry,0,1)
  self.assertEqual(parts[0],('loc',123));self.assertEqual(parts[1],', dirty, scanner unavailable, here')
 def test_group_preview_also_announces_condition(self):
  self.set(value(15129,15131));self.entry.role=''
  ns={'lang':sys.modules['tyjokr_a11y_lang'],'_entries':lambda:[self.entry],
   '_group_key':lambda:'PLUMBING','_label_part':lambda k:('loc',1),'_current':lambda:self.entry,
   '_sub_label_part':lambda *a:None,'_name_part':lambda e:('loc',123),'_place_part':lambda e:'here'}
  self.assertEqual(self.production('_group_parts',ns)()[-1],', dirty, here.')

if __name__=='__main__':unittest.main()
