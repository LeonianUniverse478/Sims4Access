/* Execute the actual AS3 Build helper bodies against native-service fixtures.
 * Strips types only. This verifies decisions/lifecycle, not native rendering.
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
let now = 10000;
function Rectangle(x, y, width, height) {
  Object.assign(this, {x, y, width, height, left: x, top: y, right: x + width, bottom: y + height});
}
function Sprite() {
  this.visible = true; this.alpha = 1; this.x = 0; this.y = 0; this.parent = null;
  this.localToGlobal = p => ({x: this.x + p.x, y: this.y + p.y});
}
const runtime = {
  Rectangle, Sprite, Point: function(x, y) { Object.assign(this, {x, y}); },
  int: Math.trunc, getTimer: () => now,
  getQualifiedClassName: obj => obj.__class,
  A11Y_PRODUCT_RESTORE_WINDOW: 5000,
};
function method(name) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(signature, 'Missing ' + name);
  let start = signature.index + signature[0].length, i = start, depth = 1;
  while (depth && i < source.length) {
    if (source[i] === '{') depth++;
    if (source[i] === '}') depth--;
    i++;
  }
  assert.equal(depth, 0, name + ' braces');
  const types = /:\s*(?:DisplayObject|Boolean|Number|String|Object|Array|Rectangle|Sprite|Point|int|Error|Class|Event)\b(?!\s*\()/g;
  const body = source.slice(start, i - 1).replace(types, '').replace(/\s+as\s+Class\b/g, '');
  return vm.runInNewContext('(function(' + signature[1].replace(types, '') + ') {' + body + '})', runtime, {filename: name});
}
function fixture() {
  now = 10000;
  const calls = [], replies = [], listeners = {}, widgets = {};
  const inspector = widgets.BuildBuyInspector = {
    btnUndo: {enabled: false}, btnRedo: {enabled: false},
    btnSledgehammer: {Selected: false}, btnEyedropper: {Selected: false},
    btnDesignTool: {Selected: false},
    mcMoveToolPanel: {btnMoveHouse: {Selected: false}, btnMoveLot: {Selected: false}},
  };
  const layer = {children: [], addChild(child) { child.parent = this; this.children.push(child); },
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parent = null; }};
  const ctx = {
    mA11yBuildControls: true,
    mA11yBuildCursor: false, mA11yBuildX: 0, mA11yBuildY: 0, mA11yBuildStep: 16,
    mA11yBuildPositionKnown: false,
    mA11yBuildProduct: null, mA11yBuildProductLost: false,
    mA11yBuildProductModals: 0, mA11yBuildProductClosedAt: 0,
    mA11yBuildProductDropPending: false, mA11yBuildProductObserved: false,
    mA11yBuildMarker: null, mA11yBuildAimSerial: 0, mA11yBuildAimZone: '',
    mA11yBuildAimUntil: 0, mA11yBuildAimFrames: 0, mA11yBuildListeners: false,
    mA11yKeyboard: true, mA11yKeyboardLease: 12000, mA11yManagedDialog: null,
    mTooltipsLayer: layer, mode: 2, top: null, editing: false, dropdown: null,
    A11yLoadedWidget: name => widgets[name] || null,
    A11yIsLive: value => Boolean(value && value.visible),
    A11yWorldHudMode() { return this.mode; },
    A11yTopModalWidget() { return this.top; },
    A11yEditing() { return this.editing; },
    A11yCurrentDropdown() { return this.dropdown; },
    A11yClearFocus() { this.focusCleared = true; },
    A11yPostToPython: (name, data) => replies.push({name, data}),
  };
  const native = {
    zone: '12', fail: '',
    CallGameService(name, data, immediate) {
      calls.push({name, data, immediate});
      if (native.fail === name) throw new Error(name + ' unavailable');
      if (name === 'BBGetCurrentZoneId') return native.zone;
      return undefined; // Important: void native operations are not successes.
    },
    CallUIService: name => name === 'GetNavigationUpperBound' ? 650 : null,
    SendUIMessage: (name, data) => calls.push({name, data, ui: true}),
    PostServerCommand: (name, data) => replies.push({name, data}),
    AddMessageListenerByName: (name, fn) => { listeners[name] = fn; },
  };
  runtime.CommunicationManager = native;
  runtime.getDefinitionByName = name => ({
    'olympus.gamepad.LayoutAPI': {StageWidth: 1280, StageHeight: 900},
    'olympus.utils.InputUtils': {sMouseX: 400, sMouseY: 300},
    'gamedata.BuildBuy.shared.CatalogProduct': function(raw) { this.Name = raw.name; },
    'olympus.localization.LocKey': function(raw) { this.toString = () => raw.text; },
  })[name];
  for (const match of source.matchAll(/public function (A11yBuild\w+)\(/g)) ctx[match[1]] = method(match[1]);
  const requested = name => calls.filter(call => call.name === name);
  const result = () => replies.filter(row => row.name === 'a11y.buildstate').slice(-1)[0]?.data.split('|')[2];
  return {ctx, calls, replies, listeners, widgets, inspector, layer, native, requested, result};
}
let passed = 0;
function test(name, callback) { callback(); passed++; console.log('PASS ' + name); }
function aim(f) { f.ctx.A11yBuildAim(['A11y', 'buildaim', '7', '2.25', '3.5', '7.25', '1', '12']); }

test('Enabling clears catalog focus but never places', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  assert(f.ctx.mA11yBuildCursor && f.ctx.focusCleared);
  assert.equal(f.requested('SetupVirtualCursor')[0].data.onConfirmDown, 0);
  assert.equal(f.requested('SendVirtualCursorClick').length, 0);
  assert.equal(f.result(), 'on');
});
test('Catalog modal is allowed, actual dialog and text input are blocked', () => {
  for (const allowed of ['BuildBuyProductCatalog', 'BuildBuyNavigation', 'BuildBuyInventory', 'BuildBuyMagalog']) {
    const f = fixture(); f.widgets[allowed] = {}; f.ctx.top = f.widgets[allowed];
    f.ctx.A11yBuildCommand('on', 1); assert.equal(f.result(), 'on');
  }
  for (const mode of ['top', 'editing', 'dropdown', 'managed']) {
    const f = fixture();
    if (mode === 'managed') f.ctx.mA11yManagedDialog = {visible: true};
    else f.ctx[mode] = mode === 'editing' ? true : {};
    f.ctx.A11yBuildCommand('on', 1);
    assert.equal(f.result(), 'blocked'); assert.equal(f.requested('SetupVirtualCursor').length, 0);
  }
});
test('Live mode and expired lease release native cursor', () => {
  for (const reason of ['mode', 'lease']) {
    const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
    if (reason === 'mode') f.ctx.mode = 1; else now = 13000;
    f.ctx.A11yBuildFrame();
    assert.equal(f.ctx.mA11yBuildCursor, false);
    assert.equal(f.requested('SetupVirtualCursor').slice(-1)[0].data.enabled, false);
    assert.equal(f.result(), 'off');
  }
});
test('Native cursor movement clamps at viewport edges and retains chosen step', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  f.ctx.A11yBuildCommand('fine', 2); f.ctx.mA11yBuildX = 9;
  f.ctx.A11yBuildCommand('left', 3);
  assert.equal(f.ctx.mA11yBuildX, 8); assert.equal(f.ctx.mA11yBuildStep, 4);
  f.ctx.A11yBuildCommand('coarse', 4); assert.equal(f.ctx.mA11yBuildStep, 64);
  f.ctx.A11yBuildCommand('coarse', 5); assert.equal(f.ctx.mA11yBuildStep, 16);
});
test('Selected destructive and whole-lot tools cannot receive a placement click', () => {
  for (const tool of ['btnSledgehammer', 'btnEyedropper', 'btnDesignTool', 'btnMoveHouse', 'btnMoveLot']) {
    const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
    (f.inspector[tool] || f.inspector.mcMoveToolPanel[tool]).Selected = true;
    f.ctx.A11yBuildCommand('click', 2);
    assert.equal(f.result(), 'toolblocked'); assert.equal(f.requested('SendVirtualCursorClick').length, 0);
  }
});
test('Undo and redo require native enabled state and use actual native history', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('undo', 1);
  assert.equal(f.result(), 'nohistory'); assert.equal(f.requested('BBOpCommand').length, 0);
  f.inspector.btnUndo.enabled = true; f.ctx.A11yBuildCommand('undo', 2);
  assert.equal(f.requested('BBOpCommand')[0].data, 'undo');
  assert.equal(f.requested('BBUndoRedo').length, 1);
});
test('Click submits exactly one native click without manufacturing a placement result', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1); f.ctx.A11yBuildCommand('click', 2);
  assert.equal(f.requested('SendVirtualCursorClick').length, 1);
  assert.equal(f.result(), 'click');
  assert(!f.replies.some(row => /success|placed/i.test(row.data)));
});
test('Native hovered names and both native error formats preserve localized text', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  f.ctx.A11yBuildProduct({show: true, product: {name: 'Krzesło | 25%'}});
  f.ctx.A11yBuildError({hash: 42, text: 'Nie można umieścić tutaj.'});
  f.ctx.A11yBuildError({labelKey: {text: 'Przeszkoda'}, notifyType: 1});
  const feedback = f.replies.filter(row => row.name === 'a11y.buildinfo').map(row => decodeURIComponent(row.data));
  assert.deepStrictEqual(feedback, ['name|Krzesło | 25%', 'error|Nie można umieścić tutaj.', 'error|Przeszkoda']);
});
test('Grid projection waits for a native frame, uses projected pixels, never auto-clicks', () => {
  const f = fixture(); aim(f);
  const marker = f.ctx.mA11yBuildMarker;
  assert.equal(marker.mouseEnabled, false); assert.equal(marker.mouseChildren, false);
  assert.equal(f.requested('SetupVirtualCursor').length, 0);
  f.ctx.A11yBuildFrame();
  assert.equal(f.requested('SetVirtualCursorPosition').length, 0);
  marker.x = 611.2; marker.y = 277.8; // Native binder update, not our code.
  f.ctx.A11yBuildFrame();
  assert.equal(f.result(), 'aim'); assert.equal(f.ctx.mA11yBuildCursor, true);
  assert.equal(f.ctx.mA11yBuildX, 611); assert.equal(f.ctx.mA11yBuildY, 277);
  assert.equal(f.layer.children.length, 0); assert.equal(f.requested('UnbindDisplayObject').length, 1);
  assert.equal(f.requested('SendVirtualCursorClick').length, 0);
});
test('Off-screen, invisible and unchanged projections time out without enabling', () => {
  for (const invalid of ['sentinel', 'invisible', 'outside', 'nan']) {
    const f = fixture(); aim(f); const marker = f.ctx.mA11yBuildMarker;
    if (invalid !== 'sentinel') { marker.x = 600; marker.y = 300; }
    if (invalid === 'invisible') marker.visible = false;
    if (invalid === 'outside') marker.y = 700;
    if (invalid === 'nan') marker.x = NaN;
    f.ctx.A11yBuildFrame(); now = 11600; f.ctx.A11yBuildFrame();
    assert.equal(f.result(), 'aimfailed'); assert.equal(f.ctx.mA11yBuildCursor, false);
    assert.equal(f.layer.children.length, 0); assert.equal(f.requested('SetupVirtualCursor').length, 0);
  }
});
test('A valid projection arriving after its deadline cannot enable a cursor', () => {
  const f = fixture(); aim(f); f.ctx.A11yBuildFrame();
  f.ctx.mA11yBuildMarker.x = 500; f.ctx.mA11yBuildMarker.y = 300;
  now = 11600; f.ctx.A11yBuildFrame();
  assert.equal(f.result(), 'aimfailed'); assert.equal(f.ctx.mA11yBuildCursor, false);
});
test('Projection cleanup survives cancellation, native exceptions and zone replacement', () => {
  for (const cause of ['cancel', 'exception', 'zone']) {
    const f = fixture(); aim(f);
    if (cause === 'cancel') f.ctx.A11yBuildCommand('off', 8);
    else {
      if (cause === 'zone') f.native.zone = '99';
      else f.native.fail = 'BBGetCurrentZoneId';
      f.ctx.A11yBuildFrame();
    }
    assert.equal(f.layer.children.length, 0); assert.equal(f.ctx.mA11yBuildMarker, null);
    // Only the disable-time pointer re-sync (-1,-1) may appear, never a projected position.
    assert.equal(f.requested('SetVirtualCursorPosition').filter(c => c.data.x !== -1).length, 0);
  }
});
test('Invalid world coordinates and mismatched zone never bind a marker', () => {
  for (const coordinates of [['NaN', '3', '7', '1', '12'], ['2', '3', '7', '1.5', '12'], ['2', '3', '7', '1', '99']]) {
    const f = fixture(); f.ctx.A11yBuildAim(['A11y', 'buildaim', '7', ...coordinates]);
    assert.equal(f.result(), 'aimfailed'); assert.equal(f.requested('BindDisplayObject').length, 0);
  }
});
test('Explicit menu movement resumes remembered position after modal closure', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  f.ctx.mA11yBuildX = 600; f.ctx.mA11yBuildY = 350;
  f.ctx.top = {}; f.ctx.A11yBuildFrame();
  assert(!f.ctx.mA11yBuildCursor); assert(f.ctx.mA11yBuildPositionKnown);
  f.ctx.A11yBuildCommand('menu:right', 2);
  assert.equal(f.result(), 'blocked'); assert.equal(f.ctx.mA11yBuildX, 600);
  f.ctx.top = null; f.ctx.A11yBuildCommand('menu:right', 3);
  assert(f.ctx.mA11yBuildCursor); assert.equal(f.ctx.mA11yBuildX, 616);
  assert.equal(f.ctx.mA11yBuildY, 350); assert.equal(f.requested('SendVirtualCursorClick').length, 0);
});
test('Menu placement retains tool restrictions and sends only one click', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1); f.ctx.A11yBuildDisable();
  f.inspector.btnSledgehammer.Selected = true;
  f.ctx.A11yBuildCommand('menu:click', 2); assert.equal(f.result(), 'toolblocked');
  assert.equal(f.requested('SendVirtualCursorClick').length, 0);
  f.inspector.btnSledgehammer.Selected = false; f.ctx.A11yBuildCommand('menu:click', 3);
  assert.equal(f.requested('SendVirtualCursorClick').length, 1);
});
test('Menu rotation restores the native cursor position before the operation', () => {
  const f=fixture(); f.ctx.A11yBuildCommand('on',1);
  f.ctx.mA11yBuildX=650; f.ctx.mA11yBuildY=350; f.ctx.A11yBuildDisable();
  f.calls.length=0; f.ctx.A11yBuildCommand('menu:rotateleft',2);
  const positioned=f.calls.findIndex(c=>c.name==='SetVirtualCursorPosition');
  const rotated=f.calls.findIndex(c=>c.name==='BBRotateSelectedObject');
  assert(positioned>=0 && rotated>positioned);
  assert.equal(f.calls[positioned].data.x,650); assert.equal(f.calls[positioned].data.y,350);
});
test('Menu actions cannot bypass editing, dropdown, mode or expired lease', () => {
  for (const cause of ['editing','dropdown','mode','lease']) {
    const f=fixture();
    if(cause==='editing') f.ctx.editing=true;
    if(cause==='dropdown') f.ctx.dropdown={};
    if(cause==='mode') f.ctx.mode=1;
    if(cause==='lease') now=13000;
    f.ctx.A11yBuildCommand('menu:click',1);
    assert.equal(f.requested('SendVirtualCursorClick').length,0);
    assert(!f.ctx.mA11yBuildCursor);
  }
});
test('Invalid menu action is refused and ordinary move cannot resume disabled cursor', () => {
  const f=fixture(); f.ctx.A11yBuildCommand('menu:bulldoze',1);
  assert.equal(f.calls.length,0); assert.equal(f.result(),'unavailable');
  f.ctx.A11yBuildCommand('right',2); assert(!f.ctx.mA11yBuildCursor);
});
test('Leaving Build or losing lease forgets suspended position; explicit off forgets too', () => {
  for(const cause of ['mode','lease','off']) {
    const f=fixture(); f.ctx.A11yBuildCommand('on',1); f.ctx.A11yBuildDisable();
    if(cause==='mode') f.ctx.mode=1;
    if(cause==='lease') now=13000;
    if(cause==='off') f.ctx.A11yBuildCommand('off',2); else f.ctx.A11yBuildFrame();
    assert(!f.ctx.mA11yBuildPositionKnown);
  }
});
test('Explicit off releases engine cursor in a fresh Live instance even with expired lease', () => {
  const f = fixture(); f.ctx.mode = 1; now = 13000;
  f.ctx.A11yBuildCommand('off', 30);
  f.ctx.A11yBuildCommand('off', 31);
  assert.equal(f.requested('SetupVirtualCursor').length, 2);
  for (const call of f.requested('SetupVirtualCursor')) {
    assert.equal(call.data.enabled, false);
    assert.equal(call.data.restraintLeft, -1);
  }
  assert.equal(f.result(), 'off');
});
test('Layer removal releases owned cursor without another frame and ignores child removal', () => {
  const f = fixture(); const removed = method('A11yOnLayerRemoved');
  f.ctx.A11yBuildCommand('on', 1); f.calls.length = 0;
  removed.call(f.ctx, {target: {}});
  assert(f.ctx.mA11yBuildCursor); assert.equal(f.calls.length, 0);
  removed.call(f.ctx, {target: f.layer});
  assert(!f.ctx.mA11yBuildCursor); assert(!f.ctx.mA11yBuildPositionKnown);
  assert.equal(f.requested('SetupVirtualCursor').length, 1);
  assert.equal(f.requested('SetupVirtualCursor')[0].data.enabled, false);
  removed.call(f.ctx, {target: f.layer});
  assert.equal(f.requested('SetupVirtualCursor').length, 1);
});
test('Suspended owned cursor releases on layer removal but unrelated layers do not alter native cursor', () => {
  const f = fixture(); const removed = method('A11yOnLayerRemoved');
  removed.call(f.ctx, {target: f.layer}); assert.equal(f.calls.length, 0);
  f.ctx.mA11yBuildPositionKnown = true;
  removed.call(f.ctx, {target: f.layer});
  assert.equal(f.requested('SetupVirtualCursor').length, 1);
  assert.equal(f.requested('SetupVirtualCursor')[0].data.enabled, false);
  assert(!f.ctx.mA11yBuildPositionKnown);
});
test('Menu restores catalog selection before one placement; cancel never restores it', () => {
  for (const action of ['menu:click', 'menu:cancel', 'on']) {
    const f = fixture();
    const product = {__class: 'gamedata.BuildBuy.shared::CatalogProduct',
      resourceKey: {}, sculptType: 0, pondType: 0, stateIndex: 2,
      Select(...args) { f.calls.push({name: 'Select', args}); }};
    f.ctx.A11yBuildProductSelected({product});
    f.ctx.A11yBuildProductModal(true);
    f.ctx.A11yBuildProductModal(false);
    f.ctx.A11yBuildCommand(action, 3);
    assert.equal(f.requested('Select').length, action === 'menu:cancel' ? 0 : 1);
    assert.equal(f.requested('SendVirtualCursorClick').length, action === 'menu:click' ? 1 : 0);
    if (action === 'menu:click') assert(f.calls.findIndex(c => c.name === 'Select') < f.calls.findIndex(c => c.name === 'SendVirtualCursorClick'));
    if (action === 'menu:cancel') assert.equal(f.ctx.mA11yBuildProduct, null);
  }
});
test('Build frame observes selection before first cursor activation', () => {
  const f = fixture();
  f.ctx.A11yBuildFrame();
  assert(!f.ctx.mA11yBuildCursor);
  assert.equal(typeof f.listeners.BBProductSelected, 'function');
  const product = {__class: 'gamedata.BuildBuy.shared::CatalogProduct', resourceKey: {}, sculptType: 0, pondType: 0, stateIndex: 0,
    Select() { f.calls.push({name: 'Select'}); }};
  f.listeners.BBProductSelected.call(f.ctx, {product});
  f.ctx.A11yBuildProductModal(true); f.ctx.A11yBuildProductModal(false);
  f.ctx.A11yBuildCommand('on', 1);
  assert.equal(f.requested('Select').length, 1);
});
test('Layer removal clears stale modal balance and product memory', () => {
  const f = fixture(); f.ctx.mA11yBuildProductModals = 2;
  f.ctx.mA11yBuildProduct = {}; f.ctx.mA11yBuildProductLost = true;
  method('A11yOnLayerRemoved').call(f.ctx, {target: f.layer});
  assert.equal(f.ctx.mA11yBuildProductModals, 0);
  assert.equal(f.ctx.mA11yBuildProduct, null);
});
test('Owned cursor cleanup restores UI mouse routing even if native cursor release throws', () => {
  for (const fail of [null, 'SetupVirtualCursor']) {
    const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
    f.calls.length = 0; f.native.fail = fail;
    f.ctx.A11yBuildDisable();
    assert.equal(f.requested('SetMouseInputEnabled').length, 1);
    assert.equal(f.requested('SetMouseInputEnabled')[0].data, true);
    assert(!f.ctx.mA11yBuildCursor);
  }
  const f = fixture(); f.ctx.A11yBuildDisable();
  assert.equal(f.requested('SetMouseInputEnabled').length, 0);
  f.ctx.A11yBuildDisable(true);
  assert.equal(f.requested('SetMouseInputEnabled')[0].data, true);
});

test('owned disable re-syncs the engine pointer to the real mouse before restoring UI routing', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  f.calls.length = 0;
  f.ctx.A11yBuildDisable();
  const order = f.calls.filter(c => !c.ui).map(c => c.name);
  assert.deepStrictEqual(order, ['SetupVirtualCursor', 'SetVirtualCursorPosition', 'SetMouseInputEnabled']);
  const resync = f.requested('SetVirtualCursorPosition')[0];
  assert.deepStrictEqual(JSON.parse(JSON.stringify(resync.data)), {x: -1, y: -1});
  assert.equal(f.requested('SetupVirtualCursor')[0].data.enabled, false);
  assert.equal(f.requested('SetupVirtualCursor')[0].data.onConfirmDown, 0);   // our enable mapping, unchanged
});

test('forced disable re-syncs too; inactive unforced disable touches nothing; a failing resync still restores routing', () => {
  const f = fixture(); f.ctx.A11yBuildDisable();
  assert.equal(f.requested('SetVirtualCursorPosition').length, 0);
  f.ctx.A11yBuildDisable(true);
  assert.equal(f.requested('SetVirtualCursorPosition').length, 1);
  const g = fixture(); g.ctx.A11yBuildCommand('on', 1); g.native.fail = 'SetVirtualCursorPosition';
  g.ctx.A11yBuildDisable();
  assert.equal(g.requested('SetMouseInputEnabled')[0].data, true);
  assert.equal(g.ctx.mA11yBuildCursor, false);
});
const buildLogs = f => f.replies.filter(r => r.name === 'a11y.buildlog').map(r => decodeURIComponent(r.data));

test('Enable snapshots bracket native mode changes and report owned state after activation', () => {
  const f = fixture();
  const system = {IsConsole: false, UsingController: false, UsingMouseKeyboard: true};
  const resolve = runtime.getDefinitionByName;
  runtime.getDefinitionByName = name => name === 'olympus.utils.SystemUtils' ? system : resolve(name);
  const call = f.native.CallGameService;
  f.native.CallGameService = (name, data, immediate) => {
    const result = call(name, data, immediate);
    if (name === 'SetupVirtualCursor' && data.enabled) {
      system.UsingController = true; system.UsingMouseKeyboard = false;
    }
    return result;
  };
  f.ctx.A11yBuildCommand('on', 1);
  const logs = buildLogs(f);
  assert(logs.some(s => s.startsWith('enable-before owned=false') && s.includes('controller=false')));
  assert(logs.some(s => s.startsWith('enable-after owned=true') && s.includes('controller=true')));
  assert(logs.indexOf('enable native return=undefined') < logs.findIndex(s => s.startsWith('enable-after')));
});

test('Every native cleanup failure is logged without skipping later cleanup or the final snapshot', () => {
  for (const [fail, prefix] of [['SetupVirtualCursor', 'disable error='],
                               ['SetVirtualCursorPosition', 'resync error='],
                               ['SetMouseInputEnabled', 'mouse restore error=']]) {
    const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
    f.calls.length = 0; f.replies.length = 0; f.native.fail = fail;
    f.ctx.A11yBuildDisable();
    assert.deepStrictEqual(f.calls.map(c => c.name), ['SetupVirtualCursor', 'SetVirtualCursorPosition', 'SetMouseInputEnabled']);
    const logs = buildLogs(f);
    assert(logs.some(s => s.startsWith(prefix) && s.includes(fail + ' unavailable')));
    assert(logs[0].startsWith('disable-before'));
    assert(logs[logs.length - 1].startsWith('disable-after owned=false'));
    assert(!f.ctx.mA11yBuildCursor);
  }
});

test('Snapshot failures preserve independently available fields and never block cleanup', () => {
  for (const failed of ['system', 'input', 'stage']) {
    const f = fixture();
    const system = {IsConsole: false, UsingController: false, UsingMouseKeyboard: true};
    const input = {sMouseX: 123, sMouseY: 456};
    f.layer.stage = {mouseX: 789, mouseY: 654};
    runtime.getDefinitionByName = name => {
      if (name === 'olympus.utils.SystemUtils') {
        if (failed === 'system') throw new Error('system unavailable');
        return system;
      }
      if (name === 'olympus.utils.InputUtils') {
        if (failed === 'input') throw new Error('input unavailable');
        return input;
      }
      throw new Error('Unexpected lookup ' + name);
    };
    if (failed === 'stage') Object.defineProperty(f.layer, 'stage', {get() { throw new Error('stage unavailable'); }});
    f.ctx.A11yBuildDisable(true);
    assert.equal(f.requested('SetMouseInputEnabled').length, 1);
    const log = buildLogs(f).find(s => s.startsWith('disable-after'));
    assert(log.includes(failed + 'Error='));
    if (failed !== 'system') assert(log.includes('controller=false mouseKeyboard=true'));
    if (failed !== 'input') assert(log.includes('input=123,456'));
    if (failed !== 'stage') assert(log.includes('stage=789,654'));
    assert(log.length <= 390);
  }
});

test('Mode listeners register once and record null and cursor payloads after disable without native mutations', () => {
  const f = fixture(); const registered = [];
  const add = f.native.AddMessageListenerByName;
  f.native.AddMessageListenerByName = (name, fn, owner) => { registered.push(name); add(name, fn, owner); };
  f.ctx.A11yBuildCommand('on', 1); f.ctx.A11yBuildObserve(); f.ctx.A11yBuildDisable();
  f.calls.length = 0; f.replies.length = 0;
  for (const name of ['UsingControllerToggled', 'CursorModeToggled']) assert.equal(registered.filter(n => n === name).length, 1);
  f.listeners.UsingControllerToggled.call(f.ctx);
  f.listeners.CursorModeToggled.call(f.ctx, {isCursorMode: false});
  assert(buildLogs(f).includes('UsingControllerToggled payload=null'));
  assert(buildLogs(f).some(s => s.startsWith('CursorModeToggled payload=') && s.endsWith('isCursorMode=false')));
  assert(buildLogs(f).some(s => s.startsWith('CursorModeToggled owned=false')));
  assert.equal(f.calls.length, 0);
});

test('Bad mode payloads still produce a snapshot and broken log transport cannot interrupt cleanup', () => {
  const f = fixture();
  f.ctx.A11yBuildCursorModeToggled({get isCursorMode() { throw new Error('payload unavailable'); }});
  assert(buildLogs(f).some(s => s.includes('payloadError=payload unavailable')));
  assert(buildLogs(f).some(s => s.startsWith('CursorModeToggled owned=false')));
  f.ctx.A11yPostToPython = () => { throw new Error('transport unavailable'); };
  f.ctx.A11yBuildDisable(true);
  assert.deepStrictEqual(f.calls.map(c => c.name), ['SetupVirtualCursor', 'SetVirtualCursorPosition', 'SetMouseInputEnabled']);
});

test('Native enable failures are logged without claiming ownership or a completed enable snapshot', () => {
  const f = fixture(); f.native.fail = 'SetupVirtualCursor';
  f.ctx.A11yBuildEnable(new Rectangle(0, 0, 100, 100));
  assert(!f.ctx.mA11yBuildCursor);
  assert(buildLogs(f).some(s => s.startsWith('enable error=') && s.includes('SetupVirtualCursor unavailable')));
  assert(!buildLogs(f).some(s => s.startsWith('enable-after')));
});

test('Build controls start off and block all native actions and observation until enabled', () => {
  assert(/mA11yBuildControls:Boolean = false;/.test(source));
  const f = fixture(); f.ctx.mA11yBuildControls = false;
  for (const action of ['on', 'left', 'click', 'undo', 'redo', 'rotateleft', 'menu:click', 'menu:status']) {
    f.ctx.A11yBuildCommand(action, 1);
    assert.equal(f.result(), 'unavailable', action);
  }
  aim(f); f.ctx.A11yBuildEnable(new Rectangle(0, 0, 100, 100));
  f.ctx.A11yBuildObserve(); f.ctx.A11yBuildProductObserve(); f.ctx.A11yBuildFrame();
  assert.equal(f.calls.length, 0);
  assert.deepStrictEqual(Object.keys(f.listeners), []);
  assert(!f.ctx.mA11yBuildCursor);
});

test('Disabling Build controls retires cursor and remembered products once; idle off never touches native cursor', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1);
  f.ctx.mA11yBuildProduct = {}; f.ctx.mA11yBuildProductLost = true; f.ctx.mA11yBuildProductModals = 2;
  f.calls.length = 0;
  f.ctx.A11yBuildSetControls(false);
  assert.deepStrictEqual(f.calls.map(c => c.name), ['SetupVirtualCursor', 'SetVirtualCursorPosition', 'SetMouseInputEnabled']);
  assert.equal(f.result(), 'off');
  assert(!f.ctx.mA11yBuildPositionKnown && !f.ctx.mA11yBuildCursor && !f.ctx.mA11yBuildControls);
  assert.equal(f.ctx.mA11yBuildProduct, null);
  assert.equal(f.ctx.mA11yBuildProductModals, 0);
  f.calls.length = 0;
  f.ctx.A11yBuildSetControls(false); f.ctx.A11yBuildFrame();
  assert.equal(f.calls.length, 0);
  const g = fixture(); g.ctx.mA11yBuildControls = false; g.ctx.A11yBuildSetControls(false);
  assert.equal(g.calls.length, 0);
  // Python can explicitly release an owned cursor after the old UI disappeared.
  g.ctx.mode = 1; g.ctx.A11yBuildCommand('off', 2);
  assert.deepStrictEqual(g.calls.map(c => c.name), ['SetupVirtualCursor', 'SetVirtualCursorPosition', 'SetMouseInputEnabled']);
});

test('Disabling Build controls releases a suspended cursor or pending projection without reviving either', () => {
  const f = fixture(); f.ctx.mA11yBuildPositionKnown = true;
  f.ctx.A11yBuildSetControls(false);
  assert.equal(f.requested('SetupVirtualCursor')[0].data.enabled, false);
  const g = fixture(); aim(g);
  assert(g.ctx.mA11yBuildMarker);
  g.calls.length = 0; g.ctx.A11yBuildSetControls(false);
  assert.equal(g.ctx.mA11yBuildMarker, null);
  assert.equal(g.ctx.mA11yBuildAimSerial, 0);
  assert.equal(g.requested('UnbindDisplayObject').length, 1);
  g.calls.length = 0; g.ctx.A11yBuildProjectionFrame();
  g.ctx.A11yBuildCommand('menu:click', 3);
  assert.equal(g.calls.length, 0);
});

test('Registered Build callbacks cannot retain or restore products after the switch is off', () => {
  const f = fixture(); f.ctx.A11yBuildObserve(); f.ctx.A11yBuildSetControls(false);
  const product = {__class: 'gamedata.BuildBuy.shared::CatalogProduct', resourceKey: {}, sculptType: 0, pondType: 0,
    Select() { throw new Error('Disabled product must not be selected'); }};
  f.listeners.BBProductSelected.call(f.ctx, {product});
  f.listeners.SetModalVisible.call(f.ctx, true);
  f.listeners.BBActionModeChanged.call(f.ctx, null);
  assert.equal(f.ctx.mA11yBuildProduct, null);
  assert.equal(f.ctx.mA11yBuildProductModals, 0);
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
});

test('Build setting messages accept only on/off and re-enabling requires an explicit action', () => {
  const f = fixture(); f.ctx.mA11yBuildControls = false;
  const handle = method('A11yHandleEncoded');
  handle.call(f.ctx, 'A11y|buildcontrols|on');
  assert(f.ctx.mA11yBuildControls); assert(!f.ctx.mA11yBuildCursor); assert.equal(f.calls.length, 0);
  handle.call(f.ctx, 'A11y|buildcontrols|invalid');
  assert(f.ctx.mA11yBuildControls);
  handle.call(f.ctx, 'A11y|buildcontrols|off|extra');
  handle.call(f.ctx, 'A11y|buildcontrols');
  assert(f.ctx.mA11yBuildControls);
  f.ctx.A11yBuildCommand('on', 1); assert(f.ctx.mA11yBuildCursor);
  handle.call(f.ctx, 'A11y|buildcontrols|off'); assert(!f.ctx.mA11yBuildCursor);
  f.calls.length = 0; handle.call(f.ctx, 'A11y|buildcontrols|on');
  assert(!f.ctx.mA11yBuildCursor); assert.equal(f.calls.length, 0);
});

test('Feature-off cleanup remains complete when native disable throws', () => {
  const f = fixture(); f.ctx.A11yBuildCommand('on', 1); f.native.fail = 'SetupVirtualCursor';
  f.calls.length = 0; f.ctx.A11yBuildSetControls(false);
  assert.equal(f.requested('SetMouseInputEnabled')[0].data, true);
  assert(!f.ctx.mA11yBuildCursor && !f.ctx.mA11yBuildPositionKnown && !f.ctx.mA11yBuildControls);
  assert.equal(f.result(), 'off');
});

console.log(passed + ' AS source-executing Build checks passed. Native runtime verification remains required.');
