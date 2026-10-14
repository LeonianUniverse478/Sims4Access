'use strict';
// Scanner mode in the shared template: which keys the native guards consume,
// when the scanner owns input, and the exact scannermode bridge message.
// Executes the actual method bodies (types stripped) against a stub owner.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
const runtime = {now: 1000, getTimer() { return runtime.now; }};
vm.createContext(runtime);
function method(name) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(signature, 'Missing ' + name);
  let start = signature.index + signature[0].length, i = start, depth = 1;
  while (depth && i < source.length) {
    if (source[i] === '{') depth++;
    if (source[i] === '}') depth--;
    i++;
  }
  const types = /:\s*(?:DisplayObject|Boolean|Number|String|Object|Array|Rectangle|Sprite|Point|int|Error|Class|Event)\b(?!\s*\()/g;
  const body = source.slice(start, i - 1).replace(types, '');
  return vm.runInContext('(function(' + signature[1].replace(types, '') + ') {' + body + '})', runtime, {filename: name});
}
const guardValid = method('A11yGuardValid');
const scannerOwner = method('A11yScannerOwner');
const handleEncoded = method('A11yHandleEncoded');

function owner(overrides) {
  const modal = {};
  const self = Object.assign({
    mA11yScannerMode: true, mA11yKeyboard: true, mA11yKeyboardLease: 5000, mA11yStartupActive: false,
    mA11yBuildCursor: false, mA11yHudBrowsing: false, mA11yStatusScope: null,
    mA11yActiveModalRoot: null, mA11yScope: null, mA11yPendingScope: null, mA11yGuardHeld: {},
    hud: 1, editing: false, frames: 0,
    A11yWorldHudMode() { return this.hud; },
    A11yEditing() { return this.editing; },
    A11yIsLive(item) { return item === modal; },
    A11yIsModalScope(scope) { return scope === modal; },
    A11yModalFrame() { this.frames++; },
    A11yLauncherNavigation() { return null; },
    A11yScannerOwner() { return scannerOwner.call(this); },
    A11yBuildSetControls() {},
  }, overrides || {});
  self.modal = modal;
  return self;
}
let checks = 0;
function check(condition, label) { assert(condition, label); checks++; }

// Arrows: consumed in Live with the mode on, whoever owns input, even with no lease.
for (const key of [37, 38, 39, 40]) {
  check(guardValid.call(owner(), key) === true, 'arrow ' + key + ' consumed');
  check(guardValid.call(owner({mA11yKeyboardLease: 10}), key) === true, 'arrow ' + key + ' consumed without lease');
  check(guardValid.call(owner({mA11yKeyboard: false}), key) === true, 'arrow ' + key + ' consumed without keyboard flag');
  const withMenu = owner(); withMenu.mA11yActiveModalRoot = withMenu.modal;
  check(guardValid.call(withMenu, key) === true, 'arrow ' + key + ' consumed while a menu owns input');
  check(guardValid.call(owner({editing: true}), key) === false, 'arrow ' + key + ' left to a text field');
  check(guardValid.call(owner({hud: 2}), key) === false, 'arrow ' + key + ' untouched in Build');
  check(guardValid.call(owner({hud: 0}), key) === false, 'arrow ' + key + ' untouched outside the world');
  check(guardValid.call(owner({mA11yScannerMode: false}), key) === false, 'arrow ' + key + ' untouched with the mode off');
}
// Enter, Space, Backspace: only while the scanner owns input, re-derived at the key.
for (const key of [8, 13, 32]) {
  const free = owner();
  check(guardValid.call(free, key) === true && free.frames === 1, 'key ' + key + ' consumed, ownership refreshed');
  const busy = owner(); busy.mA11yActiveModalRoot = busy.modal;
  check(guardValid.call(busy, key) === true, 'key ' + key + ' still consumed for the modal owner');
  const opening = owner({A11yModalFrame() { this.mA11yScope = this.modal; }});
  check(guardValid.call(opening, key) === true && opening.mA11yScope === opening.modal, 'key ' + key + ' goes to a menu that opened since the last frame');
  check(guardValid.call(owner({mA11yKeyboardLease: 10}), key) === false, 'key ' + key + ' free without lease');
  check(guardValid.call(owner({mA11yScannerMode: false}), key) === false, 'key ' + key + ' free with the mode off');
  check(guardValid.call(owner({editing: true}), key) === false, 'key ' + key + ' free in a text field');
}
// Escape is never taken by scanner mode.
check(guardValid.call(owner(), 27) === false, 'Escape stays the game Options menu');
// Ownership predicate.
check(scannerOwner.call(owner()) === true, 'owner in plain Live');
for (const [label, overrides] of [['mode off', {mA11yScannerMode: false}], ['no keyboard', {mA11yKeyboard: false}],
    ['lease lapsed', {mA11yKeyboardLease: 10}], ['startup', {mA11yStartupActive: true}], ['Build', {hud: 2}],
    ['text field', {editing: true}], ['Build cursor', {mA11yBuildCursor: true}], ['HUD browsing', {mA11yHudBrowsing: true}],
    ['status panel', {mA11yStatusScope: {}}]]) {
  check(scannerOwner.call(owner(overrides)) === false, 'not owner: ' + label);
}
const menu = owner(); menu.mA11yActiveModalRoot = menu.modal;
check(scannerOwner.call(menu) === false, 'not owner: a menu or dialog');
const pending = owner(); pending.mA11yPendingScope = pending.modal;
check(scannerOwner.call(pending) === false, 'not owner: a scope opening');
// Bridge: exactly three fields, on/off only; each message re-arms both reports.
const bridge = owner({mA11yScannerMode: false, mA11yScannerOwnerReported: '1', mA11yScannerLiveReported: '1'});
handleEncoded.call(bridge, 'A11y|scannermode|on');
check(bridge.mA11yScannerMode === true && bridge.mA11yScannerOwnerReported === '' && bridge.mA11yScannerLiveReported === '', 'on re-arms both reports');
handleEncoded.call(bridge, 'A11y|scannermode|maybe');
handleEncoded.call(bridge, 'A11y|scannermode|off|extra');
check(bridge.mA11yScannerMode === true, 'bad payloads ignored');
handleEncoded.call(bridge, 'A11y|scannermode|off');
check(bridge.mA11yScannerMode === false, 'off');
console.log(checks + ' scanner mode checks passed');
