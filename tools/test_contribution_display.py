"""Client-pixel mapping must not apply Windows DPI scaling twice."""
import ast
import pathlib
import sys
import types

source=pathlib.Path(__file__).resolve().parents[1]/'Scripts/tyjokr_a11y_house_planner.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_client_size','_client_to_screen')]
class User32:
    width,height,left,top=2880,1800,0,0
    def GetForegroundWindow(self): return 1
    def GetClientRect(self, hwnd, pointer):
        rect=pointer._obj; rect.l=rect.t=0; rect.r=self.width; rect.b=self.height
        return 1
    def ClientToScreen(self, hwnd, pointer):
        pointer._obj.x+=self.left; pointer._obj.y+=self.top
        return 1
    def GetDpiForWindow(self, hwnd):
        raise AssertionError('DPI must not be reapplied to client coordinates')
u=User32()
build=types.ModuleType('tyjokr_a11y_plus_build'); build._user32=lambda:u; build.OFFSET=[0,0]
sys.modules[build.__name__]=build
ns={}; exec(compile(ast.Module(body=nodes),'display-check','exec'),ns)
assert ns['_client_size']()==(2880,1800)
assert ns['_client_to_screen'](1440,900)==(1440,900)
u.width,u.height,u.left,u.top=1600,1000,120,80
assert ns['_client_size']()==(1600,1000)
assert ns['_client_to_screen'](800,500)==(920,580)
print('1 contribution display scenario checks passed: native resolution and offset-window coordinates')
