"""Upstream owns integrated controls; remaining extensions are queued once."""
import ast,importlib.util,pathlib,types,unittest
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
 def test_retired_adapters_are_not_available_as_duplicate_sources(self):
  for name in ['contrib','contrib_settings','layers','wall','surfaces','room_bridge']:
   self.assertFalse((R/'contrib-reference/modules'/('tyjokr_a11y_'+name+'.py')).exists())
  for name in ['layers','wall','surfaces']:
   text=(R/'Scripts'/('tyjokr_a11y_'+name+'.py')).read_text(encoding='utf-8')
   self.assertNotIn('GetAsyncKeyState',text);self.assertNotIn('def install(',text)
 def test_local_extensions_do_not_reinstall_integrated_features(self):
  import sys
  source=(R/'Scripts/tyjokr_a11y_extensions.py').read_text()
  speech=types.SimpleNamespace(log_line=lambda *a:None)
  ns={}
  with patch.dict(sys.modules,tyjokr_a11y_speech=speech):exec(compile(source,'extensions','exec'),ns)
  calls=[];installed=[]
  def load(name):
   calls.append(name);return types.SimpleNamespace(install=lambda:installed.append(name))
  with patch('importlib.import_module',side_effect=load):ns['install']();ns['install']()
  self.assertEqual(len(calls),9);self.assertEqual(len(calls),len(set(calls)))
  self.assertEqual(len(installed),4)
  for suffix in ['contrib','contrib_settings','wall','rooms','layers','surfaces']:self.assertNotIn('tyjokr_a11y_'+suffix,calls)
 def test_scanner_schedules_remaining_extensions_on_main_pump(self):
  tree=ast.parse((R/'Scripts/tyjokr_a11y_scanner.py').read_text())
  calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='post']
  matching=[n for n in calls if n.args and isinstance(n.args[0],ast.Attribute) and isinstance(n.args[0].value,ast.Name) and n.args[0].value.id=='tyjokr_a11y_extensions' and n.args[0].attr=='install']
  self.assertEqual(len(matching),1)
 def test_custom_room_label_precedes_inferred_name(self):
  import sys
  tree=ast.parse((R/'Scripts/tyjokr_a11y_rooms.py').read_text())
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='display_name']
  ns={'label_for':lambda *a:'My bedroom','_log':lambda *a:None}
  bridge=types.SimpleNamespace(inferred_name=lambda *a:'Inferred bedroom')
  with patch.dict(sys.modules,tyjokr_a11y_room_bridge=bridge):
   exec(compile(ast.Module(body=nodes),'rooms','exec'),ns)
   self.assertEqual(ns['display_name'](7,0),'My bedroom')
   ns['label_for']=lambda *a:None
   self.assertEqual(ns['display_name'](7,0),'Inferred bedroom')
if __name__=='__main__':unittest.main()
