"""Measured UI -> client -> physical-screen boundary for build helpers.

No resolution presets or extra DPI multiplier. Native projection is read-only;
actual clicks/drags remain the existing helpers and the game's validation.
"""
import contextlib
import ctypes
import json
import math
import os
import threading
import time
from urllib.parse import unquote
import sims4.commands
import tyjokr_a11y_speech as speech
import tyjokr_a11y_display_diagnostic as display

_build = None
_frame = None
_serial = 0
_pending = {}
_lock = threading.Lock()
_local = threading.local()


def _log(kind, **data):
    speech.log_line('build coordinates: ' + json.dumps(dict(kind=kind, **data), sort_keys=True, default=str))


def _api():
    u = display._api()
    signatures = {
        'SetThreadDpiAwarenessContext': (ctypes.c_void_p, [ctypes.c_void_p]),
        'SetCursorPos': (ctypes.c_int32, [ctypes.c_int32, ctypes.c_int32]),
        'mouse_event': (None, [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_size_t]),
        'GetAsyncKeyState': (ctypes.c_short, [ctypes.c_int32]),
        'GetAncestor': (ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_uint32]),
        'keybd_event': (None, [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint32, ctypes.c_size_t]),
    }
    for name, (result, args) in signatures.items():
        fn = getattr(u, name)
        fn.restype, fn.argtypes = result, args
    return u


@contextlib.contextmanager
def physical_context(u):
    previous = u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not previous: raise RuntimeError('Per-monitor coordinate context unavailable')
    try: yield
    finally:
        if not u.SetThreadDpiAwarenessContext(previous):
            _log('dpi-restore-failed')
            raise RuntimeError('Thread DPI context could not be restored')


def window(u):
    hwnd = u.GetForegroundWindow()
    pid = ctypes.c_uint32()
    if not hwnd or not u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) or pid.value != os.getpid():
        raise RuntimeError('The game must remain focused')
    if u.GetAncestor(hwnd,3)!=hwnd:raise RuntimeError('Close the native game dialog before building')
    if u.IsIconic(hwnd): raise RuntimeError('The game window is minimized')
    rect = display.RECT(); origin = display.POINT(0, 0)
    if not u.GetClientRect(hwnd, ctypes.byref(rect)) or not u.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError('Game window geometry unavailable')
    w, h = int(rect.right-rect.left), int(rect.bottom-rect.top)
    desktop = tuple(int(u.GetSystemMetrics(i)) for i in (76,77,78,79))
    if min(w,h,desktop[2],desktop[3]) < 100: raise RuntimeError('Invalid game window dimensions')
    return (int(hwnd),origin.x,origin.y,w,h,int(u.GetDpiForWindow(hwnd)),desktop,
            int(u.GetWindowLongPtrW(hwnd,-16)))


def capture_window():
    u = _api()
    with physical_context(u): return window(u)


class Frame:
    def __init__(self, zone, width, height, mode, bounds, layout, geometry, align=''):
        if not all(math.isfinite(v) for v in (width,height,*bounds,*layout)):
            raise ValueError('Non-finite viewport')
        if not (100 <= width <= 100000 and 100 <= height <= 100000): raise ValueError('Invalid viewport')
        if mode not in ('noScale','exactFit','showAll','noBorder'): raise ValueError('Unverified stage scale mode: '+mode)
        if mode in ('showAll','noBorder') and align not in ('','T','B','L','R','TL','TR','BL','BR','LT','RT','LB','RB'):
            raise ValueError('Unknown stage alignment: '+repr(align))
        if min(layout) < 100 or not (0 <= bounds[0] < bounds[2] <= layout[0] and 0 <= bounds[1] < bounds[3] <= layout[1]):
            raise ValueError('Invalid build bounds')
        self.zone,self.width,self.height,self.mode,self.geometry=zone,width,height,mode,geometry
        self.sx,self.sy=geometry[3]/width,geometry[4]/height
        self.ox=self.oy=0.0
        if mode in ('showAll','noBorder'):
            self.sx=self.sy=(min if mode=='showAll' else max)(self.sx,self.sy)
            free_x,free_y=geometry[3]-width*self.sx,geometry[4]-height*self.sy
            self.ox=0.0 if 'L' in align else free_x if 'R' in align else free_x/2
            self.oy=0.0 if 'T' in align else free_y if 'B' in align else free_y/2
        self.bounds=(bounds[0]*width/layout[0],bounds[1]*height/layout[1],bounds[2]*width/layout[0],bounds[3]*height/layout[1])
    def client(self, x, y, offset=(0,0)):
        x,y=float(x)+offset[0],float(y)+offset[1]
        if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < self.width and 0 <= y < self.height):
            raise ValueError('Projected point is outside the game viewport')
        result=(int(round(self.ox+x*self.sx)),int(round(self.oy+y*self.sy)))
        if not (0<=result[0]<self.geometry[3] and 0<=result[1]<self.geometry[4]):raise ValueError('Projected point is cropped from the viewport')
        return result
    def clear(self,p):
        x,y=p;left,top,right,bottom=self.bounds
        return left <= x <= right and top <= y <= bottom and .02*self.width <= x <= .98*self.width and .08*self.height <= y <= .70*self.height


@sims4.commands.Command('a11y.coords_enc', command_type=sims4.commands.CommandType.Live)
def receive(text: str = '', _connection=None):
    try:
        if len(text)>3000:return False
        fields=unquote(text).split('|')
        if len(fields)!=15:return False
        ident=int(fields[0]);zone=int(fields[1]);status=fields[2]
        with _lock:job=_pending.get(ident)
        if job is None or job['zone']!=zone:return False
        if status not in ('point','viewport'):
            job['result']={'status':status};job['event'].set();return True
        values=[float(fields[i]) for i in (3,4,5,6,9,10,11,12,13,14)]
        if not all(math.isfinite(v) for v in values[2:]):return False
        if status=='point' and not all(math.isfinite(v) for v in values[:2]):return False
        job['result']={'status':status,'zone':zone,'point':tuple(values[:2]),'width':values[2],'height':values[3],
                       'mode':fields[7],'align':fields[8],'layout':tuple(values[4:6]),'bounds':tuple(values[6:10])}
        job['event'].set();return True
    except Exception as exc:
        _log('reply-rejected',error=type(exc).__name__);return False


def _measure(x,z,level,height=0.0,timeout=3.0):
    global _serial,_frame
    before=capture_window()
    with _lock:
        _serial=(_serial%2147483646)+1;ident=_serial
        job={'event':threading.Event(),'zone':None,'result':None}
        _pending[ident]=job
    def start():
        try:
            import services
            job['zone']=int(services.current_zone_id())
            y=_build.floor_height(x,z,level)+height
            _build._send_ui('A11y|coords|{}|{:.6f}|{:.6f}|{:.6f}|{}|{}'.format(ident,x,y,z,level,job['zone']))
        except Exception as exc:
            job['result']={'status':'request-error','error':type(exc).__name__};job['event'].set()
    _build.core.post(start)
    try:
        if not job['event'].wait(timeout):raise RuntimeError('Projection measurement timed out; check paired UI packages')
        result=job['result']
        if not result or result['status'] not in ('point','viewport'):raise RuntimeError('Projection refused: '+str(result))
        after=capture_window()
        if before!=after:raise RuntimeError('Game window changed during projection')
        _log('raw-measure',response=result,window=after)
        frame=Frame(result['zone'],result['width'],result['height'],result['mode'],result['bounds'],result['layout'],after,result['align'])
        _frame=frame
        _log('measure',response=result,window=after)
        return result,frame
    finally:
        with _lock:_pending.pop(ident,None)


def project(x,z,level,timeout=2.5,height=0.0):
    try:
        result,frame=_measure(x,z,level,height,timeout=max(2.5,timeout))
        return result['point'] if result['status']=='point' else None
    except Exception as exc:
        _log('project-refused',error=str(exc));return None


def _current(u):
    frame=getattr(_local,'input_frame',None) or _frame
    if frame is None:raise RuntimeError('Measure the game viewport before building')
    if window(u)!=frame.geometry:raise RuntimeError('Game focus, size, position or DPI changed; retry the operation')
    import sys
    keys=sys.modules.get('tyjokr_a11y_keys')
    if keys is not None and (getattr(keys,'_editing_active',False) or keys.blocking_active()):
        raise RuntimeError('Close the open game dialog before building')
    return frame


def stage_size():
    u=_api()
    with physical_context(u):f=_current(u);return f.width,f.height


def to_screen(x,y):
    u=_api()
    with physical_context(u):
        f=_current(u);cx,cy=f.client(x,y,_build.OFFSET)
        point=display.POINT(cx,cy)
        if not u.ClientToScreen(f.geometry[0],ctypes.byref(point)):raise RuntimeError('Client conversion failed')
        _log('convert',ui=[x,y],client=[cx,cy],screen=[point.x,point.y],window=f.geometry)
        return point.x,point.y


def _release(u):
    if getattr(_local,'down',False):
        u.mouse_event(4,0,0,0,0);_local.down=False


def move_to(x,y):
    u=_api()
    try:
        with physical_context(u):
            f=_current(u);g=f.geometry;x,y=int(round(x)),int(round(y))
            if not _build.on_main(_safe_game,f.zone):raise RuntimeError('Build Mode changed during pointer operation')
            _current(u)
            if not (g[1]<=x<g[1]+g[3] and g[2]<=y<g[2]+g[4]):raise RuntimeError('Mouse point is outside the game window')
            left,top,w,h=g[6]
            nx=int(round((x-left)*65535/max(1,w-1)));ny=int(round((y-top)*65535/max(1,h-1)))
            if not (0<=nx<=65535 and 0<=ny<=65535):raise RuntimeError('Mouse point outside virtual desktop')
            if not u.SetCursorPos(x,y):raise RuntimeError('Pointer positioning failed')
            u.mouse_event(0xc001,nx,ny,0,0)
            p=display.POINT()
            if not u.GetPhysicalCursorPos(ctypes.byref(p)) or abs(p.x-x)>2 or abs(p.y-y)>2:
                raise RuntimeError('Physical pointer did not reach the requested point')
            _local.last=(x,y)
    except Exception:
        _release(u);raise


def _safe_game(zone):
    import services
    import tyjokr_a11y_place as place
    import tyjokr_a11y_keys as keys
    return place.in_build_mode() and int(services.current_zone_id())==zone and not keys.blocking_active() and not keys._editing_active


def mouse(flags,data=0):
    u=_api()
    if flags==_build.LEFT_UP:
        u.mouse_event(flags,0,0,data,0);_local.down=False;return
    if flags!=_build.LEFT_DOWN:
        return _original_mouse(flags,data)
    try:
        with physical_context(u):
            f=_current(u)
            if not _build.on_main(_safe_game,f.zone):raise RuntimeError('Build context changed before click')
            p=display.POINT();last=getattr(_local,'last',None)
            if last is None or not u.GetPhysicalCursorPos(ctypes.byref(p)) or max(abs(p.x-last[0]),abs(p.y-last[1]))>2:
                raise RuntimeError('Pointer moved before click')
            _current(u)
            u.mouse_event(flags,0,0,data,0);_local.down=True
    except Exception:
        _release(u);raise


def clear_of_panels(point):
    try:
        u=_api()
        with physical_context(u):return _current(u).clear(point)
    except Exception:return False


def _guarded_action(original,args,shift):
    u=_api()
    with physical_context(u):
        f=_current(u)
        if shift and u.GetAsyncKeyState(0x10)&0x8000:raise RuntimeError('Release Shift before using this helper')
        _local.input_frame=f
        try:return original(*args,shift=shift)
        finally:
            _release(u)
            if shift:u.keybd_event(0x10,0x2a,2,0)
            _local.input_frame=None


def park_mouse():
    try:
        u=_api()
        with physical_context(u):
            g=window(u)
            u.SetCursorPos(g[1]+g[3]//2,g[2]+g[4]//3)
    except Exception:pass


def install():
    """Startup: the engine this module measures for. Idempotent."""
    global _build
    if _build is not None:
        return
    import tyjokr_a11y_plus_build as build
    _build = build
    _log('installed')


def _original_mouse(flags, data=0):
    import tyjokr_a11y_plus_build as build
    return build._mouse_base(flags, data)


@sims4.commands.Command('a11y.buildcoords', command_type=sims4.commands.CommandType.Live)
def preflight(delay: float=5,_connection=None):
    if not math.isfinite(delay):return False
    install()
    def work():
        def target():
            import services
            sim=services.get_active_sim()
            if sim is None:raise RuntimeError('Load a household first')
            return float(sim.position.x),float(sim.position.z),int(sim.level)
        try:
            point=_build.on_main(target)
            if point is None:raise RuntimeError('Game target unavailable')
            result,frame=_measure(*point)
            # Mapping only: never call move_to, mouse, click, drag or park.
            mapped=to_screen(*result['point']) if result['status']=='point' and frame.clear(result['point']) else None
            _log('preflight',response=result,physical_point=mapped,window=frame.geometry)
            text='Build coordinate check complete. No pointer movement or construction. See TS4 Access log.'
        except Exception as exc:
            _log('preflight-failed',error=str(exc));text='Build coordinate check failed: '+str(exc)
        _build.core.post(lambda:speech.speak(text,explicit=True))
    timer=threading.Timer(max(0,min(30,delay)),work);timer.daemon=True;timer.name='a11y_build_coordinate_check';timer.start()
    sims4.commands.CheatOutput(_connection)('Read-only projection check scheduled. Close the console and keep Build Mode focused.')
    return True
