"""Resolution-independent projection mapping and fail-closed native input."""
import importlib.util,os,pathlib,sys,threading,types,unittest
from unittest.mock import Mock,patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
commands=types.SimpleNamespace(Command=lambda *a,**k:lambda f:f,CommandType=types.SimpleNamespace(Live=1),CheatOutput=lambda c:lambda s:None)
sys.modules.update(sims4=types.SimpleNamespace(commands=commands),tyjokr_a11y_speech=types.SimpleNamespace(log_enabled=False,log_line=Mock()))
sys.modules['sims4.commands']=commands
import tyjokr_a11y_build_coordinates as c
G=(2**40,120,80,2880,1800,192,(-1920,0,4800,1800),0x94080000)
def frame(w=2880,h=1800,geometry=G,mode='noScale'):
 return c.Frame(42,w,h,mode,(8,80,w-8,h-120),(w,h),geometry)
class API:
 def __init__(self):self.events=[];self.pos=(0,0);self.dpi=1;self.restore=[];self.geometry=G;self.owner=os.getpid();self.fail_position=False
 def SetThreadDpiAwarenessContext(self,ctx):
  before=self.dpi;self.dpi=ctx.value if hasattr(ctx,'value') else ctx;self.restore.append(self.dpi);return before
 def GetForegroundWindow(self):return self.geometry[0]
 def GetWindowThreadProcessId(self,h,p):p._obj.value=self.owner;return 1
 def GetAncestor(self,h,kind):return h
 def IsIconic(self,h):return False
 def GetClientRect(self,h,p):p._obj.left=p._obj.top=0;p._obj.right=self.geometry[3];p._obj.bottom=self.geometry[4];return 1
 def ClientToScreen(self,h,p):p._obj.x+=self.geometry[1];p._obj.y+=self.geometry[2];return 1
 def GetDpiForWindow(self,h):return self.geometry[5]
 def GetSystemMetrics(self,i):return dict(zip((76,77,78,79),self.geometry[6]))[i]
 def GetWindowLongPtrW(self,h,i):return self.geometry[7]
 def SetCursorPos(self,x,y):self.events.append(('move',x,y));self.pos=(x,y);return not self.fail_position
 def GetPhysicalCursorPos(self,p):p._obj.x,p._obj.y=self.pos;return 1
 def mouse_event(self,*args):self.events.append(('mouse',)+args)
 def GetAsyncKeyState(self,key):return 0
 def keybd_event(self,*args):self.events.append(('key',)+args)
class Tests(unittest.TestCase):
 def setUp(self):
  c._frame=frame();c._pending.clear();c._local=threading.local();self.u=API()
  c._build=types.SimpleNamespace(OFFSET=[0,0],LEFT_DOWN=2,LEFT_UP=4,on_main=lambda fn,*a:True)
  self.patch=patch.object(c,'_api',return_value=self.u);self.patch.start();self.addCleanup(self.patch.stop)
  c._original_mouse=Mock()
 def test_resolution_dpi_mode_matrix_has_no_extra_dpi_multiplier(self):
  for w,h in [(800,600),(1024,768),(1280,720),(1366,768),(1600,900),(1920,1080),(1920,1200),(2560,1440),(2880,1800),(3840,2160),(5120,2880)]:
   for dpi in (96,120,144,168,192,240,288):
    for left,top in ((0,0),(120,80),(-1920,0),(0,-1080)):
     for style in (0x94080000,0x16cf0000):
      g=(1,left,top,w,h,dpi,(-6000,-3000,16000,10000),style)
      f=frame(w,h,g)
      self.assertEqual(f.client(w*.5,h*.5),(w//2,h//2))
 def test_exact_fit_backbuffer_mapping(self):
  f=frame(1920,1200,G,'exactFit');self.assertEqual(f.client(960,600),(1440,900))
 def test_200_percent_reported_game_coordinates_are_not_doubled(self):
  self.assertEqual(c.to_screen(1440,900),(1560,980));self.assertEqual(self.u.dpi,1)
 def test_window_origin_and_negative_monitor_are_applied(self):
  g=(1,-1920,20,1920,1080,144,(-1920,0,3840,1200),0x94080000)
  self.u.geometry=g;c._frame=frame(1920,1080,g)
  self.assertEqual(c.to_screen(960,540),(-960,560))
 def test_context_restored_after_exception(self):
  with self.assertRaises(ValueError):
   with c.physical_context(self.u):raise ValueError('failure')
  self.assertEqual(self.u.dpi,1)
 def test_missing_dpi_context_stops_before_input(self):
  self.u.SetThreadDpiAwarenessContext=lambda ctx:0
  with self.assertRaises(RuntimeError):c.move_to(100,100)
  self.assertFalse(self.u.events)
 def test_foreign_foreground_stops_before_input(self):
  self.u.owner=0
  with self.assertRaises(RuntimeError):c.move_to(500,500)
  self.assertFalse(self.u.events)
 def test_resize_move_dpi_and_mode_change_are_refused(self):
  for index,value in ((1,121),(3,1920),(5,144),(7,0x16cf0000)):
   changed=list(G);changed[index]=value;self.u.geometry=tuple(changed)
   with self.assertRaises(RuntimeError):c.to_screen(100,100)
 def test_owned_native_dialog_is_not_treated_as_game_canvas(self):
  self.u.GetAncestor=lambda h,kind:h+1
  with self.assertRaises(RuntimeError):c.move_to(500,500)
  self.assertFalse(self.u.events)
 def test_unknown_stage_policy_and_invalid_bounds_are_refused(self):
  with self.assertRaises(ValueError):frame(mode='unknown')
  with self.assertRaises(ValueError):c.Frame(1,1920,1080,'noScale',(0,0,0,0),(1920,1080),G)
 def test_unknown_or_outside_points_refused(self):
  for p in ((-1,1),(2880,1),(1,float('nan'))):
   with self.assertRaises(ValueError):c.to_screen(*p)
  c._frame=None
  with self.assertRaises(RuntimeError):c.to_screen(10,10)
 def test_letterbox_alignment_uses_uniform_scale_and_offsets(self):
  g=(1,0,0,1920,1200,96,(0,0,1920,1200),0)
  f=c.Frame(1,1920,1080,'showAll',(8,80,1912,960),(1920,1080),g)
  self.assertEqual(f.client(960,540),(960,600));self.assertEqual(f.client(0,0),(0,60))
  f=c.Frame(1,1920,1080,'showAll',(8,80,1912,960),(1920,1080),g,'TL')
  self.assertEqual(f.client(0,0),(0,0))
 def test_no_border_crop_and_unknown_align_are_refused(self):
  g=(1,0,0,1920,1200,96,(0,0,1920,1200),0)
  f=c.Frame(1,1920,1080,'noBorder',(8,80,1912,960),(1920,1080),g)
  self.assertEqual(f.client(960,540),(960,600))
  with self.assertRaises(ValueError):f.client(0,0)
  with self.assertRaises(ValueError):c.Frame(1,1920,1080,'showAll',(8,80,1912,960),(1920,1080),g,'?')
 def test_alignment_order_variants_map_identically(self):
  g=(1,0,0,1920,1200,96,(0,0,1920,1200),0)
  for mode in ('showAll','noBorder'):
   for a,b in [('TL','LT'),('TR','RT'),('BL','LB'),('BR','RB')]:
    first=c.Frame(1,1920,1080,mode,(8,80,1912,960),(1920,1080),g,a)
    second=c.Frame(1,1920,1080,mode,(8,80,1912,960),(1920,1080),g,b)
    self.assertEqual(first.client(960,540),second.client(960,540))
 def test_nonuniform_mapping_does_not_depend_on_alignment(self):
  for mode in ('noScale','exactFit'):
   f=c.Frame(1,1440,900,mode,(8,80,1432,780),(1440,900),G,'unrecognized')
   self.assertEqual(f.client(720,450),(1440,900))
 def test_unsafe_panel_points_not_clear(self):
  self.assertFalse(c.clear_of_panels((100,20)));self.assertFalse(c.clear_of_panels((100,1700)))
  self.assertTrue(c.clear_of_panels((1440,800)))
 def test_movement_uses_virtual_desktop_and_verifies_physical_cursor(self):
  c.move_to(1560,980)
  expected=(int(round((1560+1920)*65535/4799)),int(round(980*65535/1799)))
  self.assertIn(('mouse',0xc001,*expected,0,0),self.u.events)
  self.assertEqual(self.u.dpi,1)
 def test_no_mouse_down_without_verified_pointer(self):
  with self.assertRaises(RuntimeError):c.mouse(2)
  self.assertFalse(any(e[:2]==('mouse',2) for e in self.u.events))
 def test_pointer_movement_before_click_is_refused(self):
  c.move_to(500,500);self.u.pos=(510,500)
  with self.assertRaises(RuntimeError):c.mouse(2)
  self.assertFalse(any(e[:2]==('mouse',2) for e in self.u.events))
 def test_native_context_change_refuses_mouse_down(self):
  c.move_to(500,500);c._build.on_main=lambda *a:False
  with self.assertRaises(RuntimeError):c.mouse(2)
  self.assertFalse(any(e[:2]==('mouse',2) for e in self.u.events))
 def test_abort_after_own_mouse_down_releases_button(self):
  c.move_to(500,500);c.mouse(2);self.u.owner=0
  with self.assertRaises(RuntimeError):c.move_to(510,510)
  self.assertIn(('mouse',4,0,0,0,0),self.u.events);self.assertFalse(c._local.down)
 def test_original_click_or_drag_failure_releases_mouse_and_shift(self):
  def action(a,shift=False):c.move_to(500,500);c.mouse(2);raise ValueError('original')
  with self.assertRaisesRegex(ValueError,'original'):c._guarded_action(action,((1,1),),True)
  self.assertIn(('mouse',4,0,0,0,0),self.u.events);self.assertIn(('key',0x10,0x2a,2,0),self.u.events)
  self.assertEqual(self.u.dpi,1)
 def test_build_mode_change_during_drag_releases_button_before_another_move(self):
  c.move_to(500,500);c.mouse(2);count=len(self.u.events);c._build.on_main=lambda *a:False
  with self.assertRaises(RuntimeError):c.move_to(510,510)
  self.assertEqual(self.u.events[count:],[('mouse',4,0,0,0,0)])
 def test_wheel_actions_retain_original_handler(self):
  c.mouse(0x800,120);c._original_mouse.assert_called_once_with(0x800,120)
 def test_reply_rejects_stale_zone_and_malformed_data(self):
  job={'zone':42,'event':threading.Event(),'result':None};c._pending[1]=job
  self.assertFalse(c.receive('1|43|point|1|2|2880|1800|noScale||2880|1800|8|80|2872|1680'))
  self.assertFalse(c.receive('1|42|point|1|2|NaN|1800|noScale||2880|1800|8|80|2872|1680'))
  self.assertFalse(job['event'].is_set())
 def test_valid_reply_preserves_viewport_and_offscreen_state(self):
  job={'zone':42,'event':threading.Event(),'result':None};c._pending[1]=job
  self.assertTrue(c.receive('1|42|viewport|NaN|NaN|2880|1800|noScale||2880|1800|8|80|2872|1680'))
  self.assertTrue(job['event'].is_set());self.assertEqual(job['result']['status'],'viewport')
 def test_read_only_preflight_never_calls_input(self):
  timer=Mock();f=frame();c._build.on_main=lambda f,*a:(1,2,0);c._build.core=types.SimpleNamespace(post=lambda f:None)
  with patch.object(c,'install'),patch.object(c.threading,'Timer',return_value=timer) as make,patch.object(c,'_measure',return_value=({'status':'point','point':(1440,800)},f)),patch.object(c,'to_screen',return_value=(1560,880)),patch.object(c,'move_to') as move,patch.object(c,'mouse') as click:
   c.preflight();make.call_args[0][1]();move.assert_not_called();click.assert_not_called()
 def test_release_does_not_release_a_button_we_did_not_press(self):
  c._release(self.u);self.assertFalse(self.u.events)
 def test_project_failure_returns_no_point(self):
  with patch.object(c,'_measure',side_effect=RuntimeError('unavailable')):self.assertIsNone(c.project(1,2,0))
 def test_native_probe_roundtrip_does_not_use_legacy_aim_or_input(self):
  c._build.core=types.SimpleNamespace(post=lambda fn:fn());c._build.floor_height=lambda *a:3
  requests=[]
  def send(message):
   requests.append(message);fields=message.split('|')
   c.receive('|'.join([fields[2],fields[7],'point','1440','720','2880','1800','noScale','','2880','1800','8','80','2872','1680']))
  c._build._send_ui=send
  with patch.dict(sys.modules,services=types.SimpleNamespace(current_zone_id=lambda:42)):
   self.assertEqual(c.project(10,20,0),(1440,720))
  self.assertTrue(requests[0].startswith('A11y|coords|'));self.assertFalse(self.u.events);self.assertFalse(c._pending)
 def test_park_does_not_move_an_unfocused_window(self):
  self.u.owner=0;c.park_mouse();self.assertFalse(self.u.events)
if __name__=='__main__':unittest.main()
