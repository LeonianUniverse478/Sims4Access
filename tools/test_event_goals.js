'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
function body(name) {
  const begin = source.indexOf('public function ' + name + '(');
  const end = source.indexOf('public function ', begin + 16);
  assert(begin >= 0 && end > begin);
  return source.slice(begin, end).trim().replace(/^[^{]+/, '')
    .replace(/:\s*(?:String|int|Error)\b/g, '');
}

const valid = new Function('getTimer', body('A11yEventGoalShortcutValid'));
const world = {
  mA11yKeyboard: true, mA11yKeyboardLease: 51, A11yWorldHudMode: () => 1,
  A11yEditing: () => false, A11yModalFrame() {}, A11yIsLive: Boolean, A11yIsModalScope: Boolean
};
assert.strictEqual(valid.call(world, () => 50), true);
for (const change of [
  {mA11yKeyboard: false}, {mA11yKeyboardLease: 49}, {mA11yStartupActive: true},
  {A11yWorldHudMode: () => 2}, {A11yEditing: () => true},
  {mA11yScope: {}}, {mA11yPendingScope: {}},
  {A11yModalFrame() { this.mA11yActiveModalRoot = {}; }},
]) {
  assert.strictEqual(valid.call(Object.assign({}, world, change), () => 50), false);
}
const open = new Function('CommunicationManager', body('A11yOpenEventGoals'));
const sent = [];
const host = {A11yEventGoalShortcutValid: () => true,
  A11yPostToPython: (...args) => sent.push(args)};
const game = {CallGameService: () => '9007199254740993'};
assert.strictEqual(open.call(host, game), false); // InputAction consumes false.
assert.deepStrictEqual(sent, [['a11y.eventgoals_shortcut', 'zone:9007199254740993']]);
host.A11yEventGoalShortcutValid = () => false;
open.call(host, game);
assert.strictEqual(sent.length, 1); // Recheck if a dialog opened after the key guard.
host.A11yEventGoalShortcutValid = () => true;
open.call(host, {CallGameService() { throw Error('unavailable'); }});
assert.deepStrictEqual(sent[1], ['a11y.widget_enc', encodeURIComponent('0|0|action unavailable')]);
assert(/FromKeyBinding"\]\(86,0\)[^;]*;[\s\S]*?SetValidCheck"\]\(this\.A11yEventGoalShortcutValid\);\s+action\["CallFunction"\]\(this\.A11yOpenEventGoals\);/.test(body('A11yInstallKeyGuards')));
assert(body('A11yEventGoals').includes('this.A11yEditing()'));
assert(!source.includes('public function A11yCollectEventGoals('));
console.log('16 event goal shortcut checks passed');
