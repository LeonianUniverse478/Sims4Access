'use strict';
/* Nested list traversal: execute the production A11yTabMove and its list
 * helpers against an event planner "Select a Place" fixture, where each world
 * row of the outer list holds its own venue list (not a Scaleform runtime
 * test). Live 2026-09-26: Down from Willow Creek skipped its four visible
 * venues and went to Henford-on-Bagley.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');

function DisplayObject(name = '') { this.name = name; this.parent = null; this.stage = {}; }
function DisplayObjectContainer(name) {
  if (!new.target) return name instanceof DisplayObjectContainer ? name : null;
  DisplayObject.call(this, name); this.children = [];
}
DisplayObjectContainer.prototype = Object.create(DisplayObject.prototype);
DisplayObjectContainer.prototype.add = function(child) { child.parent = this; this.children.push(child); return child; };
DisplayObjectContainer.prototype.contains = function(item) {
  for (let node = item; node; node = node.parent) if (node === this) return true;
  return false;
};
const runtime = {DisplayObject, DisplayObjectContainer, int: Math.trunc,
  asCast: (value, Type) => value instanceof Type ? value : null};

function method(name) {
  const header = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(header, 'missing source method ' + name);
  let start = header.index + header[0].length, end = start, depth = 1;
  while (depth) { if (source[end] === '{') depth++; if (source[end] === '}') depth--; end++; }
  // A type annotation, not a conversion call such as "? 0 : int(x)".
  const types = /:\s*(?:DisplayObjectContainer|DisplayObject|Stage|Boolean|Number|String|Object|Array|int|Error)\b(?!\s*\()/g;
  const body = source.slice(start, end - 1).replace(types, '')
    .replace(/((?:Object\([\w.]+\)|[\w.]+)(?:\[[\w."]+\])*)\s+as\s+(DisplayObjectContainer|DisplayObject)/g, 'asCast($1,$2)')
    .replace(/\bis\s+(DisplayObjectContainer)\b/g, 'instanceof $1');
  return vm.runInNewContext('(function(' + header[1].replace(types, '') + '){' + body + '})', runtime, {filename: name});
}

let checks = 0;
function test(name, fn) { fn(); checks++; console.log('PASS ' + name); }

// A list: rows are its cells; the layout maps rows to data indexes.
function list(name, parent) {
  const node = (parent || new DisplayObjectContainer('scope')).add(new DisplayObjectContainer(name));
  node.isList = true;
  node.layout = {
    GetNumItems: () => node.children.length,
    GetGridIndexOfCell: cell => node.children.indexOf(cell),
    GetViewAtIndex: index => node.children[index],
  };
  return node;
}

function plannerFixture() {
  const scope = new DisplayObjectContainer('SituationCreationMain');
  const worlds = list('worlds', scope);
  const rows = {};
  for (const [world, venues] of [['Willow Creek', ['Test Residence', 'Museum', 'Park', 'Nightclub']],
    ['Henford-on-Bagley', ['Farm', 'Pub']]]) {
    const row = worlds.add(new DisplayObjectContainer(world + ' row'));
    const header = row.add(new DisplayObject(world));
    const inner = list(world + ' venues', row);
    rows[world] = {row, header, inner, cells: venues.map(venue => inner.add(new DisplayObjectContainer(venue)))};
  }
  const collected = [];
  for (const world of Object.keys(rows)) collected.push(rows[world].header, ...rows[world].cells);
  return {scope, worlds, rows, collected};
}

function manager(scope, collected) {
  const ui = {
    mTooltipsLayer: {stage: {}}, mA11yScope: scope, mA11yIdxDir: 0, mA11yNavQueue: [], mA11yPendingScope: null,
    mA11yList: null, mA11yListRoot: null, mA11yEdge: 0, mA11yFocused: null, mA11yLogicalList: null, mA11yLogicalIndex: -1,
    requests: [], focused: [],
    A11yModalFrame() {},
    A11yCollectFocusables(_scope, out) { out.push(...collected); },
    A11ySortFocusables: () => 0,
    A11yFindScrollList(item) { for (let node = item; node; node = node.parent) if (node.isList) return node; return null; },
    A11yGridLayout: node => node.layout,
    A11yIndexScroll: null,
    A11yRequestIndex(target, index, direction) {
      this.requests.push([target.name, index, direction]);
      this.focus(target.layout.GetViewAtIndex(index));
      return true;
    },
    A11yFocusItem(item) { this.focused.push(item.name); this.focus(item); },
    focus(item) {
      this.mA11yFocused = item;
      this.mA11yLogicalList = this.A11yFindScrollList(item);
      this.mA11yLogicalIndex = this.mA11yLogicalList ? this.A11yCellIndexOf(this.mA11yLogicalList.layout, item) : -1;
    },
  };
  for (const name of ['A11yTabMove', 'A11yEnterNestedList', 'A11yStepInList', 'A11yIndexScroll', 'A11yCellIndexOf', 'A11yIsInside']) {
    ui[name] = method(name).bind(ui);
  }
  return ui;
}

function walk(ui, start, moves) {
  ui.focus(start);
  const said = [];
  for (const move of moves) { ui.A11yTabMove(move); said.push(ui.mA11yFocused.name); }
  return said;
}

test('Down from a world enters its venues, walks them, then continues at the next world', () => {
  const f = plannerFixture(), ui = manager(f.scope, f.collected);
  const wc = f.rows['Willow Creek'];
  assert.deepStrictEqual(walk(ui, wc.header, [1, 1, 1, 1, 1]),
    ['Test Residence', 'Museum', 'Park', 'Nightclub', 'Henford-on-Bagley row']);
  assert.deepStrictEqual(ui.requests[0], ['Willow Creek venues', 0, 1]);
  assert.deepStrictEqual(ui.requests[ui.requests.length - 1], ['worlds', 1, 1]);   // the adjacent world, not the first
});

test('Up from the next world enters the previous world\'s venues at the last one, then back to its header', () => {
  const f = plannerFixture(), ui = manager(f.scope, f.collected);
  const henford = f.rows['Henford-on-Bagley'];
  assert.deepStrictEqual(walk(ui, henford.header, [-1, -1, -1, -1, -1]),
    ['Nightclub', 'Park', 'Museum', 'Test Residence', 'Willow Creek row']);
  assert.deepStrictEqual(ui.requests[0], ['Willow Creek venues', 3, -1]);
  assert.deepStrictEqual(ui.requests[ui.requests.length - 1], ['worlds', 0, -1]);
});

test('independent lists keep first/last entry', () => {
  const scope = new DisplayObjectContainer('scope');
  const first = list('first', scope), second = list('second', scope);
  const a = [first.add(new DisplayObjectContainer('a1')), first.add(new DisplayObjectContainer('a2'))];
  const b = [second.add(new DisplayObjectContainer('b1')), second.add(new DisplayObjectContainer('b2'))];
  const ui = manager(scope, [...a, ...b]);
  assert.deepStrictEqual(walk(ui, a[1], [1]), ['b1']);
  assert.deepStrictEqual(ui.requests, [['second', 0, 1]]);
  ui.requests.length = 0;
  assert.deepStrictEqual(walk(ui, b[0], [-1]), ['a2']);
  assert.deepStrictEqual(ui.requests, [['first', 1, -1]]);
});

test('a plain list still steps by data index', () => {
  const scope = new DisplayObjectContainer('scope');
  const only = list('only', scope);
  const cells = ['r1', 'r2', 'r3'].map(name => only.add(new DisplayObjectContainer(name)));
  const ui = manager(scope, cells);
  assert.deepStrictEqual(walk(ui, cells[0], [1, 1]), ['r2', 'r3']);
  assert.deepStrictEqual(ui.requests, [['only', 1, 1], ['only', 2, 1]]);
});

console.log(checks + ' nested list checks passed (not in-game verification).');
