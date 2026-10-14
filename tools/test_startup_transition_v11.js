/* Execute the actual Flash handoff bodies against a small transport fixture.
 * This checks state-machine behavior, not Scaleform compilation or runtime. */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');

function method(name, runtime) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(signature, 'missing method ' + name);
  const start = signature.index + signature[0].length;
  let cursor = start, depth = 1;
  while (depth && cursor < source.length) {
    if (source[cursor] === '{') depth++;
    if (source[cursor] === '}') depth--;
    cursor++;
  }
  assert.strictEqual(depth, 0);
  const types = /:\s*(?:DisplayObject|Object|String|Boolean|Array|Error|Number|uint|int)\b/g;
  return vm.runInNewContext('(function(' + signature[1].replace(types, '') + ') {' +
    source.slice(start, cursor - 1).replace(types, '') + '})', runtime);
}

function fixture(active = true) {
  const native = [], socket = [];
  const ui = {
    mA11yStartupActive: active, mA11yZoneSeen: false,
    mA11yStartupKeys: [9], mA11yGuardHeld: {9: true}, mA11yModalReported: '10',
    mA11yStartupPostWindow: 10000, mA11yStartupPostCount: 40,
    A11yInstallGameMessageHook() { this.installed = true; },
    A11yStartupWrite(line) { socket.push(line); return true; },
  };
  const runtime = {getTimer: () => 10000,
    CommunicationManager: {PostServerCommand(command, payload) {
      native.push([command, payload]); return true;
    }}};
  ui.A11yPostToPython = method('A11yPostToPython', runtime);
  ui.A11yMsgHook = method('A11yMsgHook', runtime);
  return {ui, native, socket};
}

let passed = 0;
function test(name, run) { run(); passed++; console.log('PASS ' + name); }

test('Zone hook releases startup ownership and reports native mode despite exhausted speech budget', () => {
  const {ui, native, socket} = fixture();
  ui.A11yMsgHook();
  assert.strictEqual(ui.mA11yStartupActive, false);
  assert.strictEqual(ui.mA11yZoneSeen, true);
  assert.strictEqual(ui.installed, true);
  assert.strictEqual(ui.mA11yStartupKeys.length, 0);
  assert.strictEqual(Object.keys(ui.mA11yGuardHeld).length, 0);
  assert.deepStrictEqual(native, [['a11y.mark', 'startup-v11-native']]);
  assert.deepStrictEqual(socket, []);
});

test('Repeated loaded-zone hooks do not repeatedly announce a transition', () => {
  const {ui, native} = fixture();
  ui.A11yMsgHook();
  ui.A11yMsgHook();
  assert.strictEqual(native.length, 1);
});

test('Startup mode marks bypass narration throttling without releasing speech flood', () => {
  const {ui, native, socket} = fixture();
  ui.A11yPostToPython('a11y.widget_enc', 'hover');
  ui.A11yPostToPython('a11y.mark', 'startup-v11-active');
  assert.deepStrictEqual(socket, ['POST|a11y.mark|startup-v11-active']);
  assert.deepStrictEqual(native, []);
});

test('Loaded mode notifications do not depend on a live socket', () => {
  const {ui, native} = fixture();
  ui.A11yStartupWrite = () => { throw Error('socket must not be used'); };
  ui.A11yMsgHook();
  assert.deepStrictEqual(native, [['a11y.mark', 'startup-v11-native']]);
});

const GameStates = {MAIN_MENU: 1273744144, ENTER_MAIN_MENU: 3712041429, CAS: 983016380, PLAY: 270579719, BUILD: 2919482169};
function stateFixture(state, zoneSeen, hudMode) {
  return {
    mA11yZoneSeen: zoneSeen,
    mA11yGameStateSeen: 0,
    A11yGameState: () => state,
    A11yPostToPython: () => {},
    A11yWorldHudMode: () => hudMode,
    A11yLoadedWidget: () => null,
    A11yIsLive: () => false,
    zoneless: method('A11yStartupZoneless', {GameStates,
      CommunicationManager: {CallGameService: () => state}}),
  };
}
test('Returning to the main menu releases native ownership despite a retained HUD', () => {
  for (const state of [GameStates.MAIN_MENU, GameStates.ENTER_MAIN_MENU]) {
    const ui = stateFixture(state, true, 1);
    assert.strictEqual(ui.zoneless(), true);
    assert.strictEqual(ui.mA11yZoneSeen, false);
  }
});
test('New-game CAS remains zoneless even if a previous lot HUD is retained', () => {
  const ui = stateFixture(GameStates.CAS, false, 1);
  assert.strictEqual(ui.zoneless(), true);
  assert.strictEqual(ui.mA11yZoneSeen, false);
});
test('Editing CAS from a loaded lot retains native transport ownership', () => {
  const ui = stateFixture(GameStates.CAS, true, 0);
  assert.strictEqual(ui.zoneless(), false);
});
test('Live and Build state use native transport before their HUD appears', () => {
  for (const state of [GameStates.PLAY, GameStates.BUILD]) {
    const ui = stateFixture(state, false, 0);
    assert.strictEqual(ui.zoneless(), false);
    assert.strictEqual(ui.mA11yZoneSeen, true);
  }
});
test('Unknown game states retain the existing boot and zone fallback', () => {
  assert.strictEqual(stateFixture(null, false, 0).zoneless(), true);
  assert.strictEqual(stateFixture(null, true, 0).zoneless(), false);
});

test('Game-state accessor finds the UI ancestor and reads later transitions from the cached manager', () => {
  const manager = {mGameState: GameStates.PLAY, layoutMgr: {}, parent: null};
  const ui = {mA11yUIManager: null, mTooltipsLayer: {parent: {parent: manager}}};
  const getState = method('A11yGameState', {uint: Number, Number});
  assert.strictEqual(getState.call(ui), GameStates.PLAY);
  assert.strictEqual(ui.mA11yUIManager, manager);
  manager.mGameState = GameStates.MAIN_MENU;
  assert.strictEqual(getState.call(ui), GameStates.MAIN_MENU);
});
test('Missing UI ancestor returns unknown so startup fallback remains available', () => {
  const ui = {mA11yUIManager: null, mTooltipsLayer: {parent: null}};
  assert.strictEqual(method('A11yGameState', {uint: Number, Number}).call(ui), 0);
});

console.log(passed + ' startup transition checks passed.');
