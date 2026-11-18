"""Read-only event-goal requests: identity, timeouts and menu routing."""
import ast,pathlib,sys,types,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'Scripts'))
import tyjokr_a11y_event_goals as g
from urllib.parse import unquote
class Tests(unittest.TestCase):
 def setUp(self):
  g._pending=None;g._serial=0;g._registered=False;self.zone=9007199254740993
  self.hub=types.SimpleNamespace(_event=Mock(return_value=(object(),object())),_ui=Mock())
  self.speech=types.SimpleNamespace(log_line=Mock(),speak=Mock())
  self.services=types.SimpleNamespace(current_zone_id=lambda:self.zone)
  self.timers=[]
  def timer(seconds,fn):
   instance=types.SimpleNamespace(start=Mock(),callback=fn,daemon=False);self.timers.append(instance);return instance
  self.patches=[patch.dict(sys.modules,services=self.services,tyjokr_a11y_hub=self.hub,tyjokr_a11y_pump=types.SimpleNamespace(post=Mock()),tyjokr_a11y_narrator=types.SimpleNamespace(_decode_percent=unquote),tyjokr_a11y_lang=types.SimpleNamespace(t=lambda s:s),tyjokr_a11y_speech=self.speech),patch.object(g,'_register'),patch.object(g.threading,'Timer',side_effect=timer)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def test_request_keeps_exact_large_event_and_zone_identity(self):
  self.assertTrue(g.open_goals(18446744073709551000));self.hub._ui.assert_called_once_with('A11y|eventgoals|18446744073709551000|9007199254740993|1')
  self.assertTrue(self.timers[0].daemon);self.timers[0].start.assert_called_once()
 def test_ended_event_does_not_send_a_native_request(self):
  self.hub._event.return_value=(None,None)
  self.assertFalse(g.open_goals(4));self.hub._ui.assert_not_called();self.assertEqual(self.timers,[])
 def test_opened_acknowledgement_does_not_interrupt_native_goal_narration(self):
  g.open_goals(4);self.assertTrue(g.receive('1%7C9007199254740993%7Copened'));self.speech.speak.assert_not_called();self.assertIsNone(g._pending)
 def test_wrong_request_or_zone_cannot_complete_a_current_request(self):
  g.open_goals(4)
  for reply in ['2|9007199254740993|opened','1|8|opened','garbage']:
   self.assertFalse(g.receive(reply));self.assertIsNotNone(g._pending)
  self.assertTrue(g.receive('1|9007199254740993|opened'))
 def test_zone_change_discards_acknowledgement_and_timeout_speech(self):
  g.open_goals(4);self.zone=8
  self.assertFalse(g.receive('1|9007199254740993|opened'));g._expire(1);self.speech.speak.assert_not_called()
 def test_old_timeout_does_not_cancel_a_newer_request(self):
  g.open_goals(4);g.open_goals(5);g._expire(1);self.assertEqual(g._pending['event'],5);self.speech.speak.assert_not_called()
 def test_missing_ui_reply_reports_unavailable_once(self):
  g.open_goals(4);g._expire(1);g._expire(1);self.speech.speak.assert_called_once_with('event goals unavailable',explicit=True)
 def test_native_refusal_does_not_complete_or_end_the_event(self):
  g.open_goals(4);self.assertFalse(g.receive('1|9007199254740993|blocked'))
  self.speech.speak.assert_called_once_with('event goals unavailable',explicit=True)
  self.assertEqual(self.hub._ui.call_count,1)
 def test_stale_reply_is_discarded(self):
  g.open_goals(4);g._pending['until']=0
  self.assertFalse(g.receive('1|9007199254740993|opened'));self.speech.speak.assert_not_called()
 def test_event_menu_adds_goals_without_replacing_existing_end_actions(self):
  root=pathlib.Path(__file__).resolve().parents[1]
  tree=ast.parse((root/'Scripts/tyjokr_a11y_hub.py').read_text())
  code=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='event_actions'])
  captured=[];goals=Mock();ended=Mock()
  namespace={'_event':lambda sid:(object(),types.SimpleNamespace(display_name='Native event')),'menu':types.SimpleNamespace(_raw=lambda s:s),'lang':types.SimpleNamespace(t=lambda s:s),'_window':lambda *a,**k:captured.append(a),'event_goals':goals,'end_event':ended}
  exec(compile(code,'native_event_actions','exec'),namespace);namespace['event_actions'](42)
  rows=captured[0][2];self.assertEqual(len(rows),4);self.assertEqual(rows[0][0],'current event goals');rows[0][2]();goals.assert_called_once_with(42);ended.assert_not_called()
if __name__=='__main__':unittest.main()
