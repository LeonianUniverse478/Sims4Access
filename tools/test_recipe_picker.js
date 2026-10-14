'use strict';
/* Recipe grid picker (PickersGrid movie, unpatched): execute the production
 * traversal and activation bodies against a RowCellView fixture. Live
 * 2026-09-26 (TS4 Access 0506): Enter did nothing in the grill and bar food
 * lists. The row is a CellView wrapper; its CLICK listener is on the child
 * mcRowButton (RowCellViewButton extends Button). Rows with serving sizes
 * expand into LinkedRowCellView buttons on click. Not a Scaleform runtime
 * test; the movie gate and live checks remain necessary.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');

function initObject(self, name, kind, box) {
  self.name = name; self.kind = kind; self.parent = null; self.visible = true; self.alpha = 1;
  self.box = box || {x: 0, y: 0, w: 100, h: 20}; self.stage = {stageWidth: 1693, stageHeight: 1030};
}
function DisplayObject(name = '', kind = 'flash.display::DisplayObject', box) { initObject(this, name, kind, box); }
DisplayObject.prototype.getBounds = function() {
  const b = this.box;
  return {x: b.x, y: b.y, width: b.w, height: b.h, left: b.x, top: b.y, right: b.x + b.w, bottom: b.y + b.h};
};
// Cast-call syntax (DisplayObjectContainer(x)) returns x or null; construction initialises.
function DisplayObjectContainer(name, kind, box) {
  if (!new.target) return name instanceof DisplayObjectContainer ? name : null;
  initObject(this, name, kind, box); this.children = [];
}
DisplayObjectContainer.prototype = Object.create(DisplayObject.prototype);
DisplayObjectContainer.prototype.add = function(child) { child.parent = this; this.children.push(child); return child; };
DisplayObjectContainer.prototype.getChildAt = function(index) { return this.children[index]; };
DisplayObjectContainer.prototype.contains = function(item) {
  for (let node = item; node; node = node.parent) if (node === this) return true;
  return false;
};
Object.defineProperty(DisplayObjectContainer.prototype, 'numChildren', {get() { return this.children.length; }});
function MovieClip(name, kind, box) {
  if (!new.target) return name instanceof MovieClip ? name : null;
  initObject(this, name, kind, box); this.children = []; this.currentLabel = 'default';
}
MovieClip.prototype = Object.create(DisplayObjectContainer.prototype);
function Button(name, kind, box) {
  if (!new.target) return name instanceof Button ? name : null;
  initObject(this, name, kind, box); this.children = []; this.currentLabel = 'default';
  this.enabled = true; this.mouseEnabled = true;
}
Button.prototype = Object.create(MovieClip.prototype);
function SimpleButton() { if (!new.target) return null; }
function TextField(name, text) {
  if (!new.target) return name instanceof TextField ? name : null;
  initObject(this, name, 'flash.text::TextField'); this.text = text; this.type = 'dynamic';
}
TextField.prototype = Object.create(DisplayObject.prototype);
const runtime = {
  DisplayObject, DisplayObjectContainer, MovieClip, Button, SimpleButton, TextField,
  Rectangle: function(x, y, width, height) { Object.assign(this, {x, y, width, height}); },
  getQualifiedClassName: value => value.kind, int: Math.trunc,
  asCast: (value, Type) => value instanceof Type ? value : null, getTimer: () => 10000,
  MouseEvent: {MOUSE_DOWN: 'mouseDown', MOUSE_UP: 'mouseUp', CLICK: 'click'},
};

function method(name) {
  const header = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(header, 'missing source method ' + name);
  let start = header.index + header[0].length, end = start, depth = 1;
  while (depth) { if (source[end] === '{') depth++; if (source[end] === '}') depth--; end++; }
  const types = /:\s*(?:DisplayObjectContainer|DisplayObject|TextField|MovieClip|Stage|Sprite|Boolean|Number|String|Object|Array|Rectangle|int|Error)\b(?!\s*\()/g;
  const body = source.slice(start, end - 1).replace(types, '')
    .replace(/((?:Object\([\w.]+\)|[\w.]+)(?:\[[\w."]+\])*)\s+as\s+(DisplayObjectContainer|DisplayObject|TextField|Sprite)/g, 'asCast($1,$2)')
    .replace(/\s+as\s+Rectangle\b/g, '')
    .replace(/\bis\s+(TextField|MovieClip|DisplayObjectContainer|SimpleButton|Button)\b/g, 'instanceof $1');
  return vm.runInNewContext('(function(' + header[1].replace(types, '') + '){' + body + '})', runtime, {filename: name});
}

let checks = 0;
function test(name, fn) { fn(); checks++; console.log('PASS ' + name); }

const ROW = 'widgets.Pickers.controls.GridPicker::RowCellView';
const ROW_BUTTON = 'widgets.Pickers.controls.GridPicker::RowCellViewButton';
const LINKED = 'widgets.Pickers.controls.GridPicker::LinkedRowCellView';

// The recycled list layout of GridPicker.mcScrollList.
function gridList(name, parent, box) {
  const list = parent.add(new DisplayObjectContainer(name, 'olympus.views::GridView', box));
  list.layout = {
    kind: 'olympus.layout::SelectableRecyclingGridLayout',
    GetNumItems: () => list.children.length,
    GetGridIndexOfCell: cell => list.children.indexOf(cell),
    GetViewAtIndex: index => list.children[index],
  };
  list.GetGridLayout = () => list.layout;
  return list;
}

// One recipe row as PickersGrid draws it: wrapper, real button with the
// column texts, expand icon, and the linked servings grid (filled when open).
function recipeRow(list, index, label, servings = [], opened = false, enabled = true) {
  const y = 100 + index * 80;
  const row = list.add(new DisplayObjectContainer('row' + index, ROW, {x: 300, y, w: 700, h: 60}));
  row.mcRowButton = row.add(new Button('mcRowButton', ROW_BUTTON, {x: 300, y, w: 700, h: 40}));
  row.mcRowButton.enabled = enabled;
  const columns = row.mcRowButton.add(new DisplayObjectContainer('mcColumnGrid', 'olympus.views::GridView', {x: 300, y, w: 700, h: 40}));
  columns.add(new TextField('txtName', label));
  columns.add(new TextField('txtPrice', '20'));
  row.mcExpandIcon = row.add(new MovieClip('mcExpandIcon', 'flash.display::MovieClip', {x: 980, y, w: 20, h: 20}));
  row.mcLinkedGridView = row.add(new DisplayObjectContainer('mcLinkedGridView', 'olympus.views::GridView', {x: 320, y: y + 40, w: 680, h: 20 * servings.length}));
  row.servings = [];
  if (opened) {
    servings.forEach((serving, i) => {
      const cell = row.mcLinkedGridView.add(new Button(serving, LINKED, {x: 320, y: y + 40 + i * 20, w: 680, h: 18}));
      cell.add(new TextField('txtOptionName', serving));
      row.servings.push(cell);
    });
  }
  return row;
}

function pickerFixture(spec) {
  const root = new DisplayObjectContainer('root', 'widgets.Pickers::PickersMain', {x: 0, y: 0, w: 1400, h: 900});
  const picker = root.add(new DisplayObjectContainer('picker', 'widgets.Pickers.controls.GridPicker::GridPicker', {x: 250, y: 50, w: 800, h: 800}));
  const list = gridList('mcScrollList', picker, {x: 250, y: 90, w: 800, h: 600});
  const rows = spec.map((s, i) => recipeRow(list, i, s.label, s.servings || [], Boolean(s.opened), s.enabled !== false));
  return {root, picker, list, rows};
}

function manager(root) {
  const ui = {
    mA11ySimplifiedMenus: true, mA11yScope: root, mA11yActiveModalRoot: root, mTooltipsLayer: {stage: root.stage},
    mA11yMotiveLinks: {}, mA11yKeyboard: true, mA11yIdxDir: 0, mA11yNavQueue: [], mA11yPendingScope: null,
    mA11yList: null, mA11yListRoot: null, mA11yEdge: 0, mA11yFocused: null, mA11yLogicalList: null, mA11yLogicalIndex: -1,
    mA11yActivating: false, mA11yFocusPending: null, mA11yFocusDue: 0,
    dispatched: [], announced: [], focused: [], requests: [],
    A11ySimplifiedActive: () => true, A11yModalFrame() {}, A11ySeasonActivate: () => false, A11yActivateCASName: () => false,
    A11yCalendarAddOwner: () => null, A11ySingleFilterLabel: () => null, A11yInListViewport: () => true,
    A11yIntersectsStage: () => true, A11yCanRevealOnStage: () => false, A11yHiddenHireControl: () => false,
    A11yPickerFooter: () => false, A11yConfirmSinglePicker: () => false, A11yCalendarSchedule() {}, A11yClearFocus() {},
    A11yOptionsScoped: () => false, A11ySortBlock: item => item,
    A11ySafeDispatch(target, type) { this.dispatched.push([target.name, type]); },
    A11yAnnounceDisplay(item, channel) { this.announced.push([item.name, channel]); },
    A11yRequestIndex(list, index, direction) {
      this.requests.push([index, direction]);
      this.A11yFocusCell(list.layout.GetViewAtIndex(index));
      return true;
    },
    A11yFocusItem(item) {
      this.focused.push(item.name);
      this.mA11yFocused = item;
      this.mA11yLogicalList = this.A11yFindScrollList(item);
      this.mA11yLogicalIndex = this.mA11yLogicalList ? this.A11yCellIndexOf(this.A11yGridLayout(this.mA11yLogicalList), item) : -1;
    },
  };
  for (const name of ['A11yIsFocusable', 'A11ySaveChoice', 'A11yCASNameLabel', 'A11ySemanticTarget', 'A11yTextDecoration',
    'A11yKeyboardDecoration', 'A11yDialogCloseButton', 'A11yInformational', 'A11yCompositeRow', 'A11yActionProxy',
    'A11yCollectFocusables', 'A11ySortBounds', 'A11ySortFocusables', 'A11yIsLive', 'A11yIsInside', 'A11yGridLayout',
    'A11yFindScrollList', 'A11yCellIndexOf', 'A11yPickerToggleCell', 'A11yFocusCell', 'A11yActivate', 'A11yInventoryMenu',
    'A11yTabMove', 'A11yStepInList', 'A11yIndexScroll', 'A11yEnterNestedList']) {
    ui[name] = method(name).bind(ui);
  }
  return ui;
}

function names(items) { return items.map(item => item.name); }

test('the recipe row wrapper is a composite, a lookalike is not', () => {
  const ui = manager(new DisplayObjectContainer('root', 'widgets.Pickers::PickersMain'));
  assert.equal(ui.A11yCompositeRow(new DisplayObjectContainer('row', ROW)), true);
  assert.equal(ui.A11yCompositeRow(new DisplayObjectContainer('row', 'widgets.Pickers.controls.GridPicker::RowCellViewX')), false);
  assert.equal(ui.A11yCompositeRow(new DisplayObjectContainer('row', 'widgets.Pickers.controls.PickerCells::ObjectPickerCellView')), false);
  ui.mA11ySimplifiedMenus = false;
  assert.equal(ui.A11yCompositeRow(new DisplayObjectContainer('row', ROW)), true, 'not gated on Simplified menus');
});

test('a closed row yields its real button only', () => {
  const f = pickerFixture([{label: 'Grilled Cheese', servings: ['1 serving', '4 servings']}]);
  const ui = manager(f.root), out = [];
  ui.A11yCollectFocusables(f.root, out, 0);
  assert.deepStrictEqual(names(out), ['mcRowButton']);
  assert.equal(out[0], f.rows[0].mcRowButton);
  assert.equal(ui.A11yIsFocusable(f.rows[0].mcRowButton), true);
  assert.equal(ui.A11yActionProxy(f.rows[0].mcRowButton), f.rows[0].mcRowButton);
});

test('an opened row yields its button, then its servings in order', () => {
  const f = pickerFixture([{label: 'Grilled Cheese', servings: ['1 serving', '4 servings', '8 servings'], opened: true}]);
  const ui = manager(f.root), out = [];
  ui.A11yCollectFocusables(f.root, out, 0);
  out.sort(ui.A11ySortFocusables);
  assert.deepStrictEqual(names(out), ['mcRowButton', '1 serving', '4 servings', '8 servings']);
});

test('a disabled row is still a stop; Enter reads it instead of clicking', () => {
  const f = pickerFixture([{label: 'Lobster', enabled: false}]);
  const ui = manager(f.root), out = [];
  ui.A11yCollectFocusables(f.root, out, 0);
  assert.deepStrictEqual(names(out), ['mcRowButton']);
  ui.A11yFocusItem(f.rows[0].mcRowButton);
  ui.A11yActivate(true);
  assert.deepStrictEqual(ui.dispatched, []);
  assert.deepStrictEqual(ui.announced, [['mcRowButton', 'a11y.widget_enc']]);
});

test('Enter clicks the real button, never the wrapper', () => {
  const f = pickerFixture([{label: 'Garden Salad'}]);
  const ui = manager(f.root);
  ui.A11yFocusItem(f.rows[0].mcRowButton);
  ui.A11yActivate(true);
  assert.deepStrictEqual(ui.dispatched, [['mcRowButton', 'mouseDown'], ['mcRowButton', 'mouseUp'], ['mcRowButton', 'click']]);
  assert.equal(ui.A11yPickerToggleCell(f.rows[0].mcRowButton), false, 'no object-picker toggle reread');
});

test('Enter on a serving clicks that serving', () => {
  const f = pickerFixture([{label: 'Grilled Cheese', servings: ['1 serving', '4 servings'], opened: true}]);
  const ui = manager(f.root);
  ui.A11yFocusItem(f.rows[0].servings[1]);
  ui.A11yActivate(true);
  assert.deepStrictEqual(ui.dispatched.map(d => d[0]), ['4 servings', '4 servings', '4 servings']);
});

test('virtualized focus after an index scroll lands on the row button', () => {
  const f = pickerFixture([{label: 'A'}, {label: 'B'}, {label: 'C'}]);
  const ui = manager(f.root);
  ui.A11yFocusCell(f.rows[2]);
  assert.equal(ui.mA11yFocused, f.rows[2].mcRowButton);
  assert.equal(ui.mA11yLogicalIndex, 2);
  assert.equal(ui.A11yCellIndexOf(f.list.layout, f.rows[2].mcRowButton), 2, 'a child resolves to its row index');
});

test('Down walks the open servings before the next recipe; Up steps by recipe', () => {
  const f = pickerFixture([{label: 'Grilled Cheese', servings: ['1 serving', '4 servings'], opened: true}, {label: 'Salad'}]);
  const ui = manager(f.root);
  ui.A11yFocusItem(f.rows[0].mcRowButton);
  const seen = [];
  for (let i = 0; i < 3; i++) { ui.A11yTabMove(1); seen.push(ui.mA11yFocused.name); }
  assert.deepStrictEqual(seen, ['1 serving', '4 servings', 'mcRowButton']);
  assert.equal(ui.mA11yFocused, f.rows[1].mcRowButton);
  assert.deepStrictEqual(ui.requests, [[1, 1]]);
  // Up from the next recipe steps by list index and lands on the previous
  // recipe's button; its open servings are skipped on the way up (they stay
  // reachable with Down). Documented current behaviour, not a requirement.
  ui.A11yTabMove(-1);
  assert.equal(ui.mA11yFocused, f.rows[0].mcRowButton);
  ui.A11yTabMove(1);
  assert.equal(ui.mA11yFocused.name, '1 serving');
  ui.A11yTabMove(-1);
  assert.equal(ui.mA11yFocused, f.rows[0].mcRowButton, 'Up from the first serving returns to its recipe');
});

test('closed rows step by data index, one Enter-able button per recipe', () => {
  const f = pickerFixture([{label: 'A'}, {label: 'B'}, {label: 'C'}]);
  const ui = manager(f.root);
  ui.A11yFocusItem(f.rows[0].mcRowButton);
  ui.A11yTabMove(1); ui.A11yTabMove(1);
  assert.equal(ui.mA11yFocused, f.rows[2].mcRowButton);
  assert.deepStrictEqual(ui.requests, [[1, 1], [2, 1]]);
});

console.log(checks + ' recipe picker checks passed (not in-game verification).');
