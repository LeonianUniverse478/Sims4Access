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
    .replace(/for each\(suffix in fields\)/g, 'for (suffix of fields)')
    .replace(/Object\(node\)\["(dd|lb)" \+ suffix\] as DisplayObject/g, 'asCast(Object(node)["$1" + suffix],DisplayObject)')
    .replace(/:\s*\*/g, '')
    .replace(/Object\(item\)\[fields\[index\]\]\s+as\s+DisplayObject/g, 'asCast(Object(item)[fields[index]],DisplayObject)')
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
  const ui = {A11yTextValue: field => field.text, A11yIsLive: value => !!value && value.visible, A11yJoinedText: value => value.label || ''};
  ui.A11yGraphicsRowLabel = method('A11yGraphicsRowLabel').bind(ui);
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

const optionControl = method('A11yOptionsControl');
const optionState = method('A11yCheckboxState');
const actionProxy = method('A11yActionProxy');
function nativeRow(type) {
  const row = new DisplayObjectContainer('row', 'widgets.OptionsMenu.controls::OptionsCellView');
  row.lbLabel = row.add(new DisplayObjectContainer('lbLabel', 'olympus.controls::JustifiedLabel'));
  row.lbLabel.textField = row.lbLabel.add(new TextField('textField', 'Auto Age:'));
  for (const [name, kind] of [['cbCheckbox', 'Checkbox'], ['ddDropdown', 'DropdownButton'], ['tbTextButton', 'TextButton']]) {
    row[name] = row.add(new DisplayObjectContainer(name, 'olympus.gui.buttons::' + kind));
    row[name].visible = name === type; row[name].enabled = true;
    row[name].add(new TextField('text', name === 'ddDropdown' ? 'Yes' : 'Ok'));
  }
  row.cbCheckbox.Selected = true;
  row.txtDescription = row.add(new TextField('txtDescription', 'Explanation')); row.txtDescription.visible = false;
  row.txtInformation = row.add(new TextField('txtInformation', 'Information')); row.txtInformation.visible = false;
  return row;
}
function optionUi() {
  const ui = labelUi();
  ui.A11yIsLive = value => !!value && value.visible;
  ui.A11yOptionsControl = optionControl.bind(ui);
  ui.A11ySingleFilterLabel = () => null;
  ui.A11yPickerToggleCell = () => false;
  ui.A11yPlexInfo = () => null;
  ui.A11yCheckboxState = optionState.bind(ui);
  ui.A11yActionProxy = actionProxy.bind(ui);
  ui.A11yCollectText = (value, lines) => {
    if (!value || !value.visible) return;
    if (value instanceof TextField) lines.push('0|0|' + value.text);
    else for (const child of value.children || []) ui.A11yCollectText(child, lines);
  };
  return ui;
}
test('each option type routes to its visible native control, including disabled controls', () => {
  const ui = optionUi();
  for (const type of ['cbCheckbox', 'ddDropdown', 'tbTextButton']) {
    const row = nativeRow(type);
    assert.equal(ui.A11yActionProxy(row), row[type]);
    row[type].enabled = false;
    assert.equal(ui.A11yActionProxy(row), row[type]);
  }
});
test('dropdowns never announce hidden checkbox state or hidden placeholder text', () => {
  const ui = optionUi(), row = nativeRow('ddDropdown'), lines = ['old hidden Ok'];
  ui.A11yOptionsRowLabel(row, lines);
  assert.deepStrictEqual(lines, ['0|0|Auto Age:', '0|0|Yes']);
  assert.equal(ui.A11yCheckboxState(row), '');
});
test('checkbox reads current selection without its unlabelled Ok artwork', () => {
  const ui = optionUi(), row = nativeRow('cbCheckbox'), lines = [];
  ui.A11yOptionsRowLabel(row, lines);
  assert.deepStrictEqual(lines, ['0|0|Auto Age:']);
  assert.equal(ui.A11yCheckboxState(row), 'checked');
  row.cbCheckbox.Selected = false;
  assert.equal(ui.A11yCheckboxState(row), 'unchecked');
});
test('description rows and unrelated controls do not acquire an action or checkbox state', () => {
  const ui = optionUi(), row = nativeRow(null);
  assert.equal(ui.A11yOptionsControl(row), null);
  assert.equal(ui.A11yCheckboxState(row), '');
  const other = new DisplayObject('other', 'widgets.Pickers::OptionsCellView');
  other.cbCheckbox = nativeRow('cbCheckbox').cbCheckbox;
  assert.equal(ui.A11yOptionsControl(other), null);
  assert.equal(ui.A11yActionProxy(other), other);
});
test('visible native descriptions remain readable and option subclasses work', () => {
  const ui = optionUi(), row = nativeRow('ddDropdown'), lines = [];
  row.kind = 'widgets.OptionsMenu.controls::GameplayTabOptionsCellView';
  row.txtDescription.visible = true;
  ui.A11yOptionsRowLabel(row, lines);
  assert.deepStrictEqual(lines, ['0|0|Auto Age:', '0|0|Yes', '0|0|Explanation']);
});
test('checkbox proxy activation schedules a settled state reread without selecting dropdown values', () => {
  assert(source.includes('else if(getQualifiedClassName(_loc2_).indexOf("widgets.OptionsMenu.controls::") == 0 && this.A11yOptionsControl(_loc2_) != null && getQualifiedClassName(this.A11yOptionsControl(_loc2_)).indexOf("Checkbox") >= 0)'));
});
const graphicsFields = ['DisplayType','Resolution','RefreshRate','SceneRes','SimQuality','ObjQuality','LightingQuality','ReflectionQuality','EdgeSmooth','VisualEffect','ViewDistance','VisualQuality'];
function graphicsFixture(kind='DefaultGraphicsTab') {
  const tab=new DisplayObjectContainer('graphics','widgets.OptionsMenu.controls.tabs::'+kind);
  for(const suffix of graphicsFields) {
    tab['dd'+suffix]=tab.add(new DisplayObjectContainer('dd'+suffix,'olympus.gui.buttons::DropdownButton'));
    tab['lb'+suffix]=tab.add(new DisplayObject('lb'+suffix));tab['lb'+suffix].label='Localized '+suffix;
  }
  return tab;
}
test('all twelve Graphics dropdowns read their localized name before the value on Windows and Mac',()=>{
  for(const kind of ['GraphicsTab','DefaultGraphicsTab','MacGraphicsTab']) for(const suffix of graphicsFields) {
    const tab=graphicsFixture(kind),ui=labelUi(),value=tab['dd'+suffix].add(new TextField('value','Low')),lines=['0|0|Low'];
    ui.A11yOptionsRowLabel(value,lines);
    assert.deepStrictEqual(lines,['-999998|0|Localized '+suffix,'0|0|Low']);
  }
});
test('Graphics button focus gets one label and does not alter native control state',()=>{
  const tab=graphicsFixture(),ui=labelUi(),control=tab.ddResolution,lines=['0|0|2880x1800'];
  control.enabled=false;ui.A11yOptionsRowLabel(control,lines);
  assert.deepStrictEqual(lines,['-999998|0|Localized Resolution','0|0|2880x1800']);assert.equal(control.enabled,false);
});
test('hidden and missing Graphics labels preserve the value',()=>{
 for(const missing of [false,true]) {
  const tab=graphicsFixture(),ui=labelUi(),lines=['0|0|Low'];
  if(missing) delete tab.lbSimQuality;else tab.lbSimQuality.visible=false;
  ui.A11yOptionsRowLabel(tab.ddSimQuality,lines);assert.deepStrictEqual(lines,['0|0|Low']);
 }
});
test('Graphics popup choices, checkboxes and unrelated tabs retain their existing speech',()=>{
 const ui=labelUi(),tab=graphicsFixture(),check=tab.add(new DisplayObject('check')),popup=new DisplayObjectContainer('popup','olympus.gui.lists::ExpandableList');
 for(const control of [check,popup.add(new TextField('choice','High')),graphicsFixture('OtherTab').ddSimQuality]) {
  const lines=['0|0|original'];ui.A11yOptionsRowLabel(control,lines);assert.deepStrictEqual(lines,['0|0|original']);
 }
});
test('native Graphics LeftLabelCheckBox reports its actual Selected state',()=>{
 const ui=optionUi(),box=new DisplayObject('cbLaptopMode','widgets.OptionsMenu::LeftLabelCheckBox');
 box.Selected=true;assert.equal(ui.A11yCheckboxState(box),'checked');
 box.Selected=false;assert.equal(ui.A11yCheckboxState(box),'unchecked');
 box.kind='unrelated::LeftLabelCheckBox';assert.equal(ui.A11yCheckboxState(box),'');
});
console.log(checks + ' Options simplified checks passed (not in-game verification).');
