'use strict';
/* Simplified Game Options: execute the production AS3 sort, block and label
 * methods against an Options layout fixture (not a Scaleform runtime test).
 * Live 2026-09-26: the category column interleaved with the settings beside
 * it (Graphics, Audio, then the Graphics setting Windowed), and dropdown rows
 * read as a bare "Off" or "Yes".
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');

function DisplayObject(name = '', kind = 'flash.display::DisplayObject', box = {x: 0, y: 0, w: 100, h: 20}) {
  this.name = name; this.kind = kind; this.parent = null; this.visible = true; this.box = box;
  this.stage = {stageWidth: 1693, stageHeight: 1030};
}
DisplayObject.prototype.getBounds = function() {
  const b = this.box;
  return {x: b.x, y: b.y, width: b.w, height: b.h, left: b.x, top: b.y, right: b.x + b.w, bottom: b.y + b.h};
};
function DisplayObjectContainer(name, kind, box) {
  if (!new.target) return name instanceof DisplayObjectContainer ? name : null;
  DisplayObject.call(this, name, kind, box); this.children = [];
}
DisplayObjectContainer.prototype = Object.create(DisplayObject.prototype);
DisplayObjectContainer.prototype.add = function(child) { child.parent = this; this.children.push(child); return child; };
DisplayObjectContainer.prototype.contains = function(item) {
  for (let node = item; node; node = node.parent) if (node === this) return true;
  return false;
};
function TextField(name, text) {
  if (!new.target) return name instanceof TextField ? name : null;
  DisplayObject.call(this, name, 'flash.text::TextField'); this.text = text;
}
TextField.prototype = Object.create(DisplayObject.prototype);
const runtime = {
  DisplayObject, DisplayObjectContainer, TextField, int: Math.trunc,
  getQualifiedClassName: value => value.kind,
  asCast: (value, Type) => value instanceof Type ? value : null,
};

function method(name) {
  const header = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(header, 'missing source method ' + name);
  let start = header.index + header[0].length, end = start, depth = 1;
  while (depth) { if (source[end] === '{') depth++; if (source[end] === '}') depth--; end++; }
  const types = /:\s*(?:DisplayObjectContainer|DisplayObject|TextField|Rectangle|Boolean|Number|String|Object|Array|int|Error)\b/g;
  const body = source.slice(start, end - 1).replace(types, '')
    .replace(/\s+as\s+Rectangle\b/g, '')
    .replace(/((?:Object\([\w.]+\)|[\w.]+)(?:\[[\w."]+\])*)\s+as\s+(DisplayObjectContainer|DisplayObject|TextField)/g, 'asCast($1,$2)')
    .replace(/\bis\s+(TextField|DisplayObjectContainer)\b/g, 'instanceof $1');
  return vm.runInNewContext('(function(' + header[1].replace(types, '') + '){' + body + '})', runtime, {filename: name});
}

let checks = 0;
function test(name, fn) { fn(); checks++; console.log('PASS ' + name); }

const sortBounds = method('A11ySortBounds'), sortFocusables = method('A11ySortFocusables');
const sortBlock = method('A11ySortBlock'), optionsScoped = method('A11yOptionsScoped');
const rowLabel = method('A11yOptionsRowLabel'), isInside = method('A11yIsInside');

// Options layout: categories in a vertical ButtonBar on the left, a native
// settings list plus two standalone settings on the right, at heights that
// interleave with the categories.
function optionsFixture(scopeKind = 'widgets.OptionsMenu::OptionsMenuMain') {
  const scope = new DisplayObjectContainer('options', scopeKind, {x: 0, y: 0, w: 1200, h: 900});
  const bar = scope.add(new DisplayObjectContainer('bbCategories', 'scaleform.clik.controls::ButtonBar', {x: 0, y: 100, w: 200, h: 400}));
  const categories = ['Gameplay', 'Graphics', 'Audio', 'Music'].map((label, index) =>
    bar.add(new DisplayObject(label, 'olympus.gui.buttons::TabButton', {x: 0, y: 100 + index * 60, w: 200, h: 40})));
  const content = scope.add(new DisplayObjectContainer('content', 'widgets.OptionsMenu.controls::TabbedContent', {x: 300, y: 90, w: 800, h: 700}));
  const windowed = content.add(new DisplayObject('Windowed', 'olympus.gui.buttons::Checkbox', {x: 300, y: 130, w: 300, h: 30}));
  const list = content.add(new DisplayObjectContainer('list', 'widgets.OptionsMenu.controls::TabScrollerView', {x: 300, y: 190, w: 800, h: 300}));
  list.isList = true;
  const cells = ['Autonomy', 'Auto Age', 'Death Inventory'].map((label, index) =>
    list.add(new DisplayObject(label, 'widgets.OptionsMenu.controls::OptionsCellView', {x: 300, y: 190 + index * 90, w: 800, h: 80})));
  const apply = content.add(new DisplayObject('Apply', 'olympus.gui.buttons::TextButton', {x: 300, y: 600, w: 200, h: 40}));
  return {scope, bar, categories, windowed, list, cells, apply};
}

function manager(scope, simplified = true, active = true) {
  const ui = {mA11ySimplifiedMenus: simplified, mA11yScope: scope,
    A11ySimplifiedActive: () => active,
    A11yFindScrollList(item) { for (let node = item; node; node = node.parent) if (node.isList) return node; return null; }};
  ui.A11ySortBounds = sortBounds.bind(ui);
  ui.A11yOptionsScoped = optionsScoped.bind(ui);
  ui.A11ySortBlock = sortBlock.bind(ui);
  ui.A11ySortFocusables = sortFocusables.bind(ui);
  return ui;
}

function order(ui, items) { return items.slice().reverse().sort(ui.A11ySortFocusables).map(item => item.name); }

test('simplified Options keeps the category column together, then the settings', () => {
  const f = optionsFixture(), ui = manager(f.scope);
  assert.deepStrictEqual(order(ui, [...f.categories, f.windowed, ...f.cells, f.apply]),
    ['Gameplay', 'Graphics', 'Audio', 'Music', 'Windowed', 'Autonomy', 'Auto Age', 'Death Inventory', 'Apply']);
});

test('a native settings list is one block: nothing sorts between its rows', () => {
  const f = optionsFixture(), ui = manager(f.scope);
  const stray = f.scope.add(new DisplayObject('Stray', 'olympus.gui.buttons::Checkbox', {x: 1150, y: 280, w: 40, h: 30}));
  const names = order(ui, [...f.cells, stray, f.windowed]);
  assert.deepStrictEqual(names, ['Windowed', 'Autonomy', 'Auto Age', 'Death Inventory', 'Stray']);
});

test('simplified off keeps the old position order (categories and settings interleave)', () => {
  const f = optionsFixture(), ui = manager(f.scope, false);
  const names = order(ui, [...f.categories, f.windowed, ...f.cells]);
  assert.deepStrictEqual(names.slice(0, 3), ['Gameplay', 'Windowed', 'Graphics']);
});

test('other menus and CAS/Stories are unchanged', () => {
  for (const [kind, active] of [['widgets.Pickers::PickersMain', true], ['widgets.OptionsMenu::OptionsMenuMain', false]]) {
    const f = optionsFixture(kind), ui = manager(f.scope, true, active);
    const names = order(ui, [...f.categories, f.windowed, ...f.cells]);
    assert.deepStrictEqual(names.slice(0, 3), ['Gameplay', 'Windowed', 'Graphics'], kind + ' ' + active);
    assert.equal(ui.A11ySortBlock(f.cells[0]), f.cells[0]);
  }
});

test('block lookup stops at the scope and returns the item outside any bar or list', () => {
  const f = optionsFixture(), ui = manager(f.scope);
  assert.equal(ui.A11ySortBlock(f.categories[2]), f.bar);
  assert.equal(ui.A11ySortBlock(f.cells[1]), f.list);
  assert.equal(ui.A11ySortBlock(f.windowed), f.windowed);
  assert.equal(ui.A11ySortBlock(null), null);
});

function optionsRow(label, labelVisible = true) {
  const cell = new DisplayObjectContainer('cell', 'widgets.OptionsMenu.controls::GameplayTabOptionsCellView');
  cell.lbLabel = {visible: labelVisible, textField: new TextField('textField', label)};
  cell.ddDropdown = cell.add(new DisplayObjectContainer('ddDropdown', 'olympus.gui.buttons::DropdownButton'));
  const value = cell.ddDropdown.add(new TextField('txtValue', 'Off'));
  cell.cbCheckbox = cell.add(new DisplayObject('cbCheckbox', 'olympus.gui.buttons::Checkbox'));
  return {cell, value};
}

function labelUi() {
  const ui = {A11yTextValue: field => field.text};
  ui.A11yIsInside = isInside.bind(ui);
  ui.A11yOptionsRowLabel = rowLabel.bind(ui);
  return ui;
}

test('a dropdown reads its row label first (native lbLabel, localized)', () => {
  const ui = labelUi(), {cell, value} = optionsRow('Autonomia:');
  for (const target of [cell.ddDropdown, value]) {
    const lines = ['0|0|Off'];
    ui.A11yOptionsRowLabel(target, lines);
    assert.deepStrictEqual(lines, ['-999998|0|Autonomia:', '0|0|Off']);
  }
});

test('no label for checkboxes, hidden labels, empty labels or other widgets', () => {
  const ui = labelUi();
  let row = optionsRow('Autonomy:');
  let lines = [];
  ui.A11yOptionsRowLabel(row.cell.cbCheckbox, lines); assert.deepStrictEqual(lines, []);
  row = optionsRow('Autonomy:', false);
  ui.A11yOptionsRowLabel(row.cell.ddDropdown, lines); assert.deepStrictEqual(lines, []);
  row = optionsRow('');
  ui.A11yOptionsRowLabel(row.cell.ddDropdown, lines); assert.deepStrictEqual(lines, []);
  const other = new DisplayObjectContainer('other', 'widgets.Pickers::PickersMain');
  ui.A11yOptionsRowLabel(other.add(new DisplayObject('btn', 'olympus.gui.buttons::DropdownButton')), lines);
  assert.deepStrictEqual(lines, []);
});

test('focus and widget announcements call the row label decorator', () => {
  assert(/this\.A11yMoveInQuote\(param1,_loc2_\);( this\.A11yTransferQuote\(param1,_loc2_\); this\.A11yMoveLabel\(param1,_loc2_\);)? this\.A11yOptionsRowLabel\(param1,_loc2_\);/.test(source));
});

console.log(checks + ' Options simplified checks passed (not in-game verification).');
