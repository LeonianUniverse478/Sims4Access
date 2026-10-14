/* Native story ownership uses actual display children; this fixture runs the
 * AS3 decision body with type annotations removed, not a Scaleform emulator. */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, 'cas_scope_v10_methods.as'), 'utf8');
function method(name, input = source) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(input);
  assert(signature, 'missing method ' + name);
  const start = signature.index + signature[0].length - 1;
  let cursor = start + 1, depth = 1;
  while (depth) {
    if (input[cursor] === '{') depth++;
    if (input[cursor] === '}') depth--;
    cursor++;
  }
  const types = /:\s*(DisplayObjectContainer|DisplayObject|Error|Event|int)\b/g;
  const body = input.slice(start + 1, cursor - 1)
    .replace(types, '')
    .replace(/\s+as\s+DisplayObjectContainer\b/g, '');
  return vm.runInNewContext('(function(' + signature[1].replace(types, '') + '){' + body + '})', {
    getQualifiedClassName: obj => obj.kind, Event: {ENTER_FRAME: 'frame'}, Dictionary: function() {},
  });
}
const scope = method('A11yCASStoryScope');
function fixture(children) {
  const root = {live: true, getChildAt: i => children[i], numChildren: children.length};
  return {root, A11yLoadedWidget: name => name === 'CASStories' ? root : null,
    A11yIsLive: item => Boolean(item && item.live), scope};
}
function dialog(live = true) { return {kind: 'widgets.CAS.Stories::CASStoriesDialog', live}; }
let passed = 0;
function test(name, run) { run(); passed++; console.log('PASS ' + name); }
test('Story dialog takes its native visible child, ignoring button and background names', () => {
  const target = dialog(), ui = fixture([{kind: 'widgets.CAS.Stories::CASStoriesDialogButton', live: true}, target,
    {kind: 'other::CASStoriesDialog', live: true}]);
  assert.strictEqual(ui.scope(), target);
});
test('Outgoing hidden story is retired while replacement dialog becomes the scope', () => {
  const old = dialog(), next = dialog(), children = [old, next], ui = fixture(children);
  assert.strictEqual(ui.scope(), next);
  next.live = false;
  assert.strictEqual(ui.scope(), old);
  old.live = false;
  assert.strictEqual(ui.scope(), null);
});
test('A cached closed CASStories widget never owns keyboard navigation', () => {
  const ui = fixture([dialog()]); ui.root.live = false;
  assert.strictEqual(ui.scope(), null);
  ui.A11yLoadedWidget = () => null;
  assert.strictEqual(ui.scope(), null);
});
test('A native display teardown fails closed without invoking a game service', () => {
  const ui = fixture([dialog()]); ui.root.getChildAt = () => { throw Error('removed'); };
  assert.strictEqual(ui.scope(), null);
});
test('A game-state switch drops queued inputs and departing widget references without hover', () => {
  const calls = [], old = dialog(), ui = {
    mA11yFocused: old, mA11yScope: old, mA11yPendingScope: old, mA11yActiveModalRoot: old,
    mA11yScopeHistory: [old], mA11yNavQueue: [0], mA11yBuildCursor: false, mA11yBuildMarker: null,
    mTooltipsLayer: {removeEventListener: (event, callback) => calls.push(event)},
    A11yFenceOpeningInput: () => calls.push('fence'), A11yCancelIndex: () => calls.push('cancel-index'),
    A11yWatchFocused: (previous, next) => { assert.strictEqual(previous, old); assert.strictEqual(next, null); },
    A11yKeyProbeOff: () => {}, A11yClearRing: () => {},
    A11yBuildDisable: () => { throw Error('inactive native cursor must be untouched'); },
    A11yFocusHover: () => { throw Error('departing widgets must not receive synthetic events'); },
  };
  method('A11yResetGameState').call(ui);
  for (const name of ['mA11yFocused', 'mA11yScope', 'mA11yPendingScope', 'mA11yActiveModalRoot', 'mA11yDropdown', 'mA11yFocusPending']) {
    assert.strictEqual(ui[name], null);
  }
  assert.strictEqual(ui.mA11yNavQueue.length, 0);
  assert.strictEqual(ui.mA11yScopeHistory.length, 0);
  assert.deepStrictEqual(calls, ['fence', 'cancel-index', 'frame', 'frame']);
});
test('Focused-control removal cannot re-enter retiring native hover handlers', () => {
  const actual = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
  const old = dialog(), calls = [], ui = {
    mA11yFocused: old, mA11yList: [old], mA11yListRoot: old,
    A11yFocusHover: () => { throw Error('unsafe re-entry'); },
    A11yWatchFocused: (previous, next) => calls.push([previous, next]),
    A11yClearRing: () => calls.push('clear-ring'),
  };
  method('A11yOnFocusedRemoved', actual).call(ui, {target: old});
  assert.strictEqual(ui.mA11yFocused, null);
  assert.strictEqual(ui.mA11yListRoot, null);
  assert.deepStrictEqual(calls, [[old, null], 'clear-ring']);
});
console.log(passed + ' CAS scope checks passed.');
