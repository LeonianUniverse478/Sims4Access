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
    .replace(/:\s*(?:String|DisplayObjectContainer|int|Error)\b/g, '');
}
const collect = new Function('item', 'result', 'depth', 'const getQualifiedClassName = item => item.kind;' +
  body('A11yCollectEventGoals').replace('item as DisplayObjectContainer', 'item.children ? item : null'));
const host = {A11yCollectEventGoals: collect};
function node(kind, children, visible = true) {
  return {kind: 'widgets.Gameplay.SituationDisplay.controls::' + kind, visible, alpha: 1,
    children, numChildren: children && children.length, getChildAt: i => children[i]};
}
const main = node('SituationMajorGoalIconContainer');
const ordinary = node('SituationGoalIconContainer');
const grid = node('SituationGoalCellView');
const hidden = node('Box', [node('ScenarioGoalCellView')], false);
const rows = [];
host.A11yCollectEventGoals(node('Box', [main, ordinary, grid, hidden]), rows, 0);
assert.deepStrictEqual(rows, [main, ordinary, grid]);

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
assert(/FromKeyBinding"\]\(86,0\)[^;]*;[\s\S]*?SetValidCheck"\]\(this\.A11yEventGoalShortcutValid\);\s+action\["CallFunction"\]\(this\.A11yOpenEventGoals\);/.test(body('A11yInstallKeyGuards')));
console.log('11 event goal checks passed');
