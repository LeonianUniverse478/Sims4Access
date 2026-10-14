/* Execute the actual AS3 traversal/label bodies against display-tree fixtures.
 * This removes type annotations/casts only; it is not a Scaleform runtime test.
 * The full movie compiler/fidelity gates and in-game checks remain necessary.
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const tooltip = fs.readFileSync(path.join(root, 'flash/TooltipManager_patched.as'), 'utf8');
const motive = fs.readFileSync(path.join(root, 'flash/extra-classes/CommodityContainer.as'), 'utf8');
const probe = fs.readFileSync(path.join(root, 'tools/key_probe_v10_methods.as'), 'utf8');

function DisplayObject(name = '', kind = 'flash.display::DisplayObject') {
  this.name = name; this.kind = kind; this.parent = null;
  this.visible = true; this.alpha = 1; this.stage = {stageWidth: 1693, stageHeight: 1030};
}
DisplayObject.prototype.getBounds = () => ({width: 100, height: 20, left: 0, top: 0, right: 100, bottom: 20});
DisplayObject.prototype.localToGlobal = () => ({x: 0, y: 0});
function DisplayObjectContainer(name = '', kind) {
  DisplayObject.call(this, name, kind); this.children = [];
}
DisplayObjectContainer.prototype = Object.create(DisplayObject.prototype);
DisplayObjectContainer.prototype.add = function(child) {
  child.parent = this; this.children.push(child); return child;
};
DisplayObjectContainer.prototype.getChildAt = function(index) { return this.children[index]; };
Object.defineProperty(DisplayObjectContainer.prototype, 'numChildren', {get() { return this.children.length; }});
function MovieClip(name = '', kind) {
  if (!new.target) return name instanceof MovieClip ? name : null;
  DisplayObjectContainer.call(this, name, kind); this.currentLabel = 'default';
}
MovieClip.prototype = Object.create(DisplayObjectContainer.prototype);
function TextField(name = '', text = '') {
  if (!new.target) return name instanceof TextField ? name : null;
  DisplayObject.call(this, name, 'flash.text::TextField'); this.text = text;
}
TextField.prototype = Object.create(DisplayObject.prototype);
const runtime = {
  DisplayObject, DisplayObjectContainer, MovieClip, TextField,
  Rectangle: function(x, y, width, height) { Object.assign(this, {x, y, width, height}); },
  Point: function(x, y) { this.x = x; this.y = y; },
  getQualifiedClassName: value => value.kind,
  int: Math.trunc,
  asCast: (value, Type) => value instanceof Type ? value : null,
  getTimer: () => 10000,
};

function method(source, name) {
  const match = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(match, 'missing source method ' + name);
  let start = match.index + match[0].length, cursor = start, depth = 1;
  // These selected methods contain no braces in strings or block comments.
  while (depth && cursor < source.length) {
    if (source[cursor] === '{') depth++;
    if (source[cursor] === '}') depth--;
    cursor++;
  }
  assert.equal(depth, 0, 'unbalanced source method ' + name);
  const types = /:\s*(?:DisplayObjectContainer|DisplayObject|TextField|MovieClip|MouseEvent|KeyboardEvent|Event|Boolean|Number|String|Object|Array|Rectangle|Sprite|Point|int|Error)\b/g;
  const parameters = match[1].replace(types, '');
  const body = source.slice(start, cursor - 1).replace(types, '')
    .replace(/((?:Object\([\w.]+\)|[\w.]+)(?:\[[\w."]+\])*)\s+as\s+(DisplayObjectContainer|DisplayObject|TextField)/g, 'asCast($1,$2)')
    .replace(/\s+as\s+Rectangle\b/g, '')
    .replace(/\bis\s+(TextField|MovieClip|DisplayObjectContainer)\b/g, 'instanceof $1');
  return vm.runInNewContext('(function(' + parameters + ') {' + body + '})', runtime, {filename: name});
}

function manager() {
  const value = {
    mA11yMotiveLinks: {}, mTooltipsLayer: null, mA11yOpening: false,
    mA11yLast: '', mA11yLastTime: 0, mA11yWindowStart: 0, mA11yWindowCount: 0,
    mA11yMarked: true,
    A11yPostToPython: (command, payload) => runtime.CommunicationManager.PostServerCommand(command, payload),
    A11yIsFocusable: item => Boolean(item.focusable),
    A11yInListViewport: () => true,
    A11ySingleFilterLabel: () => null,
    A11yTextValue: field => field.text,
    A11yFundsTarget: () => false,
    A11yRentalQuote: () => {}, // Rental context has its own source-executing suite.
    A11yMoveInQuote: () => {}, // Move-in context has its own source-executing suite.
    A11yTransferQuote: () => {}, // Transfer labels have their own suite (test_transfer_labels.js).
    A11yMoveLabel: () => {}, // Move furnishing labels: test_transfer_labels.js.
    A11yCalendarHeader: () => false,
    A11yCalendarLabel: () => '',
    A11yCompleted: () => false,
    A11yCheckboxState: () => '',
    A11yIsBareCount: () => false,
    A11yIsInside: (item, root) => { for (let node = item; node; node = node.parent) if (node === root) return true; return false; },
  };
  for (const name of ['A11yDialogCloseButton', 'A11yCASNameLabel', 'A11yIntersectsStage', 'A11yCanRevealOnStage',
    'A11yCalendarAddOwner', 'A11ySemanticTarget', 'A11yTextDecoration', 'A11yHiddenHireControl',
    'A11yKeyboardDecoration', 'A11yInformational', 'A11yCompositeRow', 'A11yActionProxy',
    'A11yCollectFocusables', 'A11yCollectText', 'A11yMapLabel', 'A11yWizardNavLabel', 'A11yChoiceDescription', 'A11yAnnounceDisplay',
    'A11yOptionsRowLabel']) {
    value[name] = method(tooltip, name);
  }
  return value;
}

let passed = 0;
function test(name, run) { run(); passed++; console.log('PASS ' + name); }
test('Event Sim hover omits hidden hiring controls but retains real hiring controls', () => {
  const ui=manager(), row=new MovieClip('row','widgets.Pickers.controls.SimPicker::SituationSimPickerCellView');
  row.add(new TextField('name','Evie Darden'));
  row.mcHireSimControl=row.add(new MovieClip('mcHireSimControl'));
  row.mcHireSimControl.add(new TextField('instruction','Hire this Role'));
  row.mcHireSimControl.add(new TextField('count','0'));
  row.mcHireSimControl.visible=false;
  let lines=[];ui.A11yCollectText(row,lines,0,false);
  assert.deepStrictEqual(lines,['0|0|Evie Darden']);
  row.mcHireSimControl.visible=true;
  lines=[];ui.A11yCollectText(row,lines,0,false);
  assert(lines.some(x=>x.includes('Hire this Role')));
  row.kind='unrelated';row.mcHireSimControl.visible=false;
  assert.equal(ui.A11yHiddenHireControl(row.mcHireSimControl),false);
});
test('Wizard navigation is reachable and labels use the native data-index mapping', () => {
  const ui = manager(), wizard = new MovieClip('wizard'); wizard.mcRoleSlotter = {};
  const grid = wizard.add(new MovieClip('mcTopNavGrid'));
  const cell = grid.add(new MovieClip('venue', 'widgets.Gameplay.SituationCreation.controls::WizardTopNavigationButton'));
  cell.focusable = true;
  const targets = []; ui.A11yCollectFocusables(wizard, targets, 0);
  assert.deepStrictEqual(targets, [cell]);
  const requested = [];
  const layout = {GetCellIndexToDataIndex: index => {assert.equal(index, 1); return 3;},
    GetDataAtIndex: index => {requested.push(index); return {label: 'Wybierz miejsce'};}};
  ui.A11yFindScrollList = () => grid; ui.A11yGridLayout = () => layout;
  ui.A11yCellIndexOf = () => 1;
  assert.equal(ui.A11yWizardNavLabel(cell), 'Wybierz miejsce');
  assert.deepStrictEqual(requested, [3]);
  const speech = [];
  runtime.CommunicationManager = {PostServerCommand: (command, payload) => speech.push(decodeURIComponent(payload))};
  ui.A11yAnnounceDisplay(cell, 'a11y.widget_enc', false);
  assert.deepStrictEqual(speech, ['0|0|Wybierz miejsce']);
  ui.A11yCellIndexOf = () => -1;
  assert.equal(ui.A11yWizardNavLabel(cell), '');
  assert.equal(ui.A11yWizardNavLabel(new MovieClip('other')), '');
});
test('Map toolbar order remains stable when hover artwork expands', () => {
  const ui = {A11ySortBounds: method(tooltip, 'A11ySortBounds'), A11ySortBlock: method(tooltip, 'A11ySortBlock'),
    A11yOptionsScoped: method(tooltip, 'A11yOptionsScoped'), mA11ySimplifiedMenus: false};
  const sort = method(tooltip, 'A11ySortFocusables').bind(ui);
  const cancel = new DisplayObject('btnCancel', 'widgets.GameEntry.WorldSelection::CancelButtonBig');
  const wall = new DisplayObject('btnWall', 'widgets.GameTray.controls::WallButton');
  let cancelHover = false, wallHover = false;
  cancel.getBounds = () => ({x: 930, y: cancelHover ? -8 : 6});
  wall.getBounds = () => ({x: 1627, y: wallHover ? -8 : 2});
  cancel.GetBoundsOverride = () => ({x: 930, y: 6});
  wall.GetBoundsOverride = () => ({x: 1627, y: 2});
  for (const hovered of ['none', 'cancel', 'wall']) {
    cancelHover = hovered === 'cancel'; wallHover = hovered === 'wall';
    assert(sort(cancel, wall) < 0, hovered);
    assert(sort(wall, cancel) > 0, hovered);
  }
  const unrelated = new DisplayObject('button', 'widgets.Other::Button');
  unrelated.getBounds = () => ({x: 10, y: 20});
  unrelated.GetBoundsOverride = () => {throw Error('unrelated widget must retain its bounds');};
  assert.deepStrictEqual(ui.A11ySortBounds(unrelated), {x: 10, y: 20});
});
test('World categories expose individual world buttons without flattening choices', () => {
  const ui = manager();
  const category = new MovieClip('worldCategory', 'widgets.GameEntry.WorldSelection.controls::WorldRegionTypeCellView');
  category.focusable = true;
  const grid = category.add(new MovieClip('mcGrid'));
  const first = grid.add(new MovieClip('world1', 'widgets.GameEntry.WorldSelection.controls::WorldCellView'));
  const second = grid.add(new MovieClip('world2', 'widgets.GameEntry.WorldSelection.controls::WorldCellView'));
  first.focusable = second.focusable = true;
  const targets = []; ui.A11yCollectFocusables(category, targets, 0);
  assert.deepStrictEqual(targets, [first, second]);
});
test('Street containers expose their native lot buttons', () => {
  const ui = manager();
  const street = new MovieClip('street', 'widgets.GameEntry.Neighborhood.controls::StreetClip');
  street.focusable = true;
  const lots = street.add(new MovieClip('mcLots'));
  const lot = lots.add(new MovieClip('lot', 'widgets.GameEntry.Neighborhood.controls::LotClip'));
  lot.focusable = true;
  const targets = []; ui.A11yCollectFocusables(street, targets, 0);
  assert.deepStrictEqual(targets, [lot]);
});
test('Map lot labels use native localized name and venue without calling travel', () => {
  const ui = manager();
  const lot = new MovieClip('lot', 'widgets.GameEntry.Neighborhood.controls::LotClip');
  lot.lotId = '123';
  lot.GetData = () => ({lotDescriptionData: {name: {toString: () => 'Custom Library'}}, venueData: {Label: 'Library'}});
  assert.equal(ui.A11yMapLabel(lot), 'Custom Library. Library');
  lot.GetData = () => null;
  assert.equal(ui.A11yMapLabel(lot), '');
  const other = new MovieClip('other'); other.lotId = '456';
  other.GetData = () => {throw Error('unrelated controls must not be queried');};
  assert.equal(ui.A11yMapLabel(other), '');
});
test('World-specific street subclasses expose lots through the native StreetClip fields', () => {
  const ui = manager();
  for (const kind of ['Street_SP', 'Street_CE', 'Street_CB', 'Street_VS_2']) {
    const street = new MovieClip('s23281', kind); street.focusable = true;
    street.mcLots = street.add(new MovieClip('mcLots'));
    street.btnStreetTag = new MovieClip('btnStreetTag');
    const lot = street.mcLots.add(new MovieClip('l123', 'Lot_123')); lot.focusable = true;
    const targets = []; ui.A11yCollectFocusables(street, targets, 0);
    assert.deepStrictEqual(targets, [lot]);
  }
});
test('World-specific lot subclass labels retain MapClipBase data and reject unrelated GetData controls', () => {
  const ui = manager(), lot = new MovieClip('l123', 'Lot_123');
  lot.lotId = '123'; lot.mcPositionHelper = new MovieClip(); lot.mcMapTag = new MovieClip();
  lot.GetData = () => ({lotDescriptionData: {name: {toString: () => 'Biblioteka'}}, venueData: {Label: 'Biblioteka publiczna'}});
  assert.equal(ui.A11yMapLabel(lot), 'Biblioteka. Biblioteka publiczna');
  delete lot.mcMapTag;
  assert.equal(ui.A11yMapLabel(lot), '');
});
test('Phone uses its native tooltip once, with a fallback only when no label exists', () => {
  for (const nativeLabel of ['Phone', 'Telefon', '']) {
    const ui = manager(), phone = new MovieClip('btnPhone', 'PhoneButton');
    phone.TooltipExt = {Text: nativeLabel};
    const speech = [];
    runtime.CommunicationManager = {PostServerCommand: (command, payload) => speech.push(decodeURIComponent(payload))};
    ui.A11yAnnounceDisplay(phone, 'a11y.widget_enc', false);
    assert.equal(speech.length, 1);
    const segments = speech[0].split('\u0001').map(value => value.slice(value.lastIndexOf('|') + 1));
    assert.deepStrictEqual(segments, [nativeLabel || 'phone']);
  }
});
test('Dialog close control is excluded while its Main Menu action remains reachable', () => {
  const ui = manager(), dialog = new MovieClip('dialog', 'widgets.Dialog.dialogs::DialogContainer');
  const close = dialog.add(new MovieClip('btnClose', 'olympus.gui.buttons::Button'));
  close.focusable = true;
  const main = dialog.add(new MovieClip('btnMainMenu', 'olympus.gui.buttons::Button'));
  main.focusable = true;
  const targets = []; ui.A11yCollectFocusables(dialog, targets, 0);
  assert.deepStrictEqual(targets, [main]);
});
test('Panel and picker close controls remain reachable', () => {
  for (const kind of ['widgets.Pickers::PickersMain', 'widgets.Gameplay::Panel']) {
    const ui = manager(), panel = new MovieClip('panel', kind);
    const close = panel.add(new MovieClip('btnClose', 'olympus.gui.buttons::Button'));
    close.focusable = true;
    const targets = []; ui.A11yCollectFocusables(panel, targets, 0);
    assert.deepStrictEqual(targets, [close]);
  }
});
function textOf(ui, item) {
  const result = []; ui.A11yCollectText(item, result, 0, false);
  return result.map(entry => entry.slice(entry.lastIndexOf('|') + 1));
}
test('Installed worlds omit dormant pack captions while locked worlds retain them', () => {
  const ui = manager(), world = new MovieClip('world', 'widgets.GameEntry.WorldSelection.controls::WorldCellView');
  world.mcWorldInfoText = world.add(new MovieClip('mcWorldInfoText'));
  world.mcWorldInfoText.add(new TextField('txtNeighborhoodName', 'Oasis Springs'));
  world.mcPackInfo = world.add(new MovieClip('mcPackInfo'));
  world.mcPackInfo.add(new TextField('txtPackName', 'Pack Name'));
  world.btnUnlock = world.add(new MovieClip('btnUnlock')); world.btnUnlock.visible = false;
  world.btnUnlock.add(new TextField('txtLabel', 'Unlock'));
  assert.deepStrictEqual(textOf(ui, world), ['Oasis Springs']);
  world.btnUnlock.visible = true;
  world.mcPackInfo.children[0].text = 'Required Expansion';
  assert.deepStrictEqual(textOf(ui, world), ['Oasis Springs', 'Required Expansion', 'Unlock']);
});
function calendarRow(kind, label) {
  const row = new MovieClip('entry', 'widgets.Gameplay.Calendar.controls::' + kind);
  row.txtLabel = row.add(new TextField('txtLabel', label));
  row.btnAdd = row.add(new MovieClip('btnAdd', 'olympus.gui.buttons::Button'));
  row.btnAdd.focusable = true;
  row.btnAdd.add(new MovieClip('icon'));
  return row;
}

test('Calendar restores every inner Add control to its native localized row label', () => {
  for (const [kind, label] of [
    ['ScheduleAddHoliday', 'Dodaj święto'], ['ScheduleAddEvent', 'Dodaj wydarzenie'],
    ['ScheduleAddWeddingEvent', 'Add Wedding Event'], ['ScheduleAddStayover', 'Add Stay Over'],
    ['ScheduleAddFuneralEvent', 'Add Funeral Event'], ['ScheduleAddGetawayEvent', 'Add Getaway'],
  ]) {
    const ui = manager(), row = calendarRow(kind, label), focus = [];
    assert.equal(ui.A11ySemanticTarget(row.btnAdd.children[0]), row);
    ui.A11yCollectFocusables(row, focus, 0);
    assert.deepStrictEqual(focus, [row]);
    assert.equal(ui.A11yActionProxy(row), row.btnAdd);
    const speech = [];
    runtime.CommunicationManager = {PostServerCommand: (command, payload) => speech.push([command, decodeURIComponent(payload)])};
    ui.A11yAnnounceDisplay(row.btnAdd, 'a11y.widget_enc', false);
    assert.deepStrictEqual(speech, [['a11y.widget_enc', '0|0|' + label]]);
  }
});

test('Calendar labels retain native rich row tooltip text', () => {
  const ui = manager(), row = calendarRow('ScheduleAddStayover', 'Dodaj nocowanie'), speech = [];
  row.TooltipExt = {Text: 'Nocowanie może trwać kilka dni.'};
  runtime.CommunicationManager = {PostServerCommand: (command, payload) => speech.push(decodeURIComponent(payload))};
  ui.A11yAnnounceDisplay(row.btnAdd, 'a11y.widget_enc', false);
  assert.equal(speech[0], '0|0|Dodaj nocowanie\u0001999998|999998|Nocowanie może trwać kilka dni.');
});

test('An unrelated Add button keeps its original semantic target', () => {
  const ui = manager(), row = calendarRow('ScheduleAddEvent', 'Add');
  row.kind = 'other.controls::ScheduleAddEvent';
  assert.equal(ui.A11ySemanticTarget(row.btnAdd), row.btnAdd);
});

test('School title anchor is skipped while the real grade header remains reachable', () => {
  const ui = manager(), career = new MovieClip('career', 'widgets.Gameplay.SimInfoHUD.CareerPanel::RegularCareerCellView');
  career.mcJobInfoCellView = new MovieClip('mcJobInfoCellView');
  const header = career.add(new MovieClip('btnExpander', 'olympus.gui.buttons::TextButton'));
  header.focusable = true; header.add(new TextField('txtLabel', 'Grade School B Student'));
  career.mcJobTitle = career.add(new MovieClip('mcJobTitle'));
  career.mcJobTitle.add(new TextField('txtTitle', 'Job Title'));
  const focus = []; ui.A11yCollectFocusables(career, focus, 0);
  assert.deepStrictEqual(focus, [header]);
  assert.deepStrictEqual(textOf(ui, career), ['Grade School B Student']);
});

test('School noEmotion summary excludes stale ideal mood but retains performance', () => {
  const ui = manager(), row = new MovieClip('mcPerformanceMood', 'widgets.Gameplay.SimInfoHUD.CareerPanel::PerformanceMoodDetails');
  row.currentLabel = 'noEmotion';
  row.add(new TextField('txtTitle', 'Grade Requirements:'));
  row.add(new TextField('txtPerformance', 'Performance: Good'));
  row.add(new TextField('txtIdealMoodTitle', 'Ideal Mood:'));
  row.add(new TextField('txtIdealMood', 'Bored'));
  assert.deepStrictEqual(textOf(ui, row), ['Grade Requirements:', 'Performance: Good']);
  row.currentLabel = 'withEmotion';
  assert.deepStrictEqual(textOf(ui, row), ['Grade Requirements:', 'Performance: Good', 'Ideal Mood:', 'Bored']);
});

test('Unrelated controls with matching field names remain narrated', () => {
  const ui = manager(), row = new MovieClip('mcJobTitle', 'another.Widget');
  row.currentLabel = 'noEmotion';
  row.add(new TextField('txtIdealMood', 'Bored'));
  assert.deepStrictEqual(textOf(ui, row), ['Bored']);
});

test('Synthetic Needs hover produces no independent duplicate; physical hover still speaks', () => {
  const calls = [], ui = {mA11ySyntheticHover: true, A11yAnnounceDisplay: (...args) => calls.push(args)};
  runtime.getDefinitionByName = name => {
    assert.equal(name, 'olympus.core.TooltipManager'); return {getInstance: () => ui};
  };
  const row = {}, rollover = method(motive, 'A11yOnMotiveRollOver');
  rollover.call(row, {});
  assert.equal(calls.length, 0);
  ui.mA11ySyntheticHover = false;
  rollover.call(row, {});
  assert.deepStrictEqual(calls, [[row, 'a11y.widget_enc', false]]);
});

test('Missing TooltipManager during teardown does not throw from Needs rollover', () => {
  runtime.getDefinitionByName = () => { throw Error('unloaded'); };
  assert.doesNotThrow(() => method(motive, 'A11yOnMotiveRollOver').call({}, {}));
});

function probeManager() {
  runtime.Event = {ENTER_FRAME: 'enterFrame', DEACTIVATE: 'deactivate'};
  runtime.KeyboardEvent = {KEY_DOWN: 'keyDown', KEY_UP: 'keyUp'};
  const events = [], actions = [], removed = [], posts = [];
  const stage = {
    addEventListener: (...args) => events.push(args),
    removeEventListener: (...args) => removed.push(args),
  };
  runtime.getDefinitionByName = name => {
    if (name.endsWith('InputTrigger')) return {FromKeyBinding: (key, modifiers) => ({key, modifiers})};
    if (name.endsWith('InputAction')) return {WhenTriggered: trigger => ({
      trigger, SetPriority() {}, AllowWhileModalOpen() {},
      SetValidCheck(callback) { this.valid = callback; }, CallFunction(callback) { this.callback = callback; },
    })};
    if (name.endsWith('InputActionManager')) return {
      RegisterAction: action => (actions.push(action), true),
      UnregisterAction: action => actions.splice(actions.indexOf(action), 1),
    };
    throw Error('unexpected lookup ' + name);
  };
  const ui = {
    mTooltipsLayer: {stage}, mA11yKeyProbeEnabled: false, mA11yKeyProbeActions: [],
    mA11yKeyProbeHeld: {}, mA11yKeyProbeLastEvent: null, mA11yKeyProbeCount: 0,
    A11yPostToPython: (command, payload) => posts.push([command, payload]),
  };
  for (const name of ['A11yKeyProbeReport', 'A11yKeyProbeStageEvent', 'A11yKeyProbeNative',
    'A11yKeyProbeValid', 'A11yKeyProbeTick', 'A11yKeyProbeOn', 'A11yKeyProbeOff']) {
    ui[name] = method(probe, name);
  }
  return {ui, events, actions, removed, posts};
}

test('Optional probe installs only non-consuming native H and removes all listeners/actions', () => {
  const {ui, events, actions, removed, posts} = probeManager();
  assert.equal(ui.mA11yKeyProbeEnabled, false);
  ui.A11yKeyProbeOn();
  assert.equal(events.length, 6);
  assert.equal(actions.length, 1);
  assert.deepStrictEqual(actions[0].trigger, {key: 72, modifiers: 6});
  assert.equal(actions[0].callback.call(ui), true); // EA negates: not consumed
  assert(posts.some(entry => entry[1] === 'keyprobe-native-down|72|-1|1|1|0'));
  ui.A11yKeyProbeOff();
  assert.equal(actions.length, 0);
  assert.equal(removed.length, 6);
  assert.equal(ui.mA11yKeyProbeEnabled, false);
});

test('Probe excludes ordinary letters, deduplicates capture/bubble, and retains key-up metadata', () => {
  const {ui, posts} = probeManager();
  ui.A11yKeyProbeOn(); posts.length = 0;
  function event(keyCode, type, ctrlKey, altKey, keyLocation = 0) {
    return {keyCode, type, ctrlKey, altKey, keyLocation, shiftKey: false,
      preventDefault() { throw Error('probe must never cancel'); },
      stopImmediatePropagation() { throw Error('probe must never consume'); }};
  }
  ui.A11yKeyProbeStageEvent(event(65, 'keyDown', false, false));
  ui.A11yKeyProbeStageEvent(event(72, 'keyDown', false, false));
  assert.equal(posts.length, 0);
  const down = event(72, 'keyDown', true, true);
  ui.A11yKeyProbeStageEvent(down); ui.A11yKeyProbeStageEvent(down);
  ui.A11yKeyProbeStageEvent(event(72, 'keyUp', false, false));
  assert.deepStrictEqual(posts.map(entry => entry[1]), [
    'keyprobe-stage-down|72|0|1|1|0', 'keyprobe-stage-up|72|0|0|0|0']);
  ui.A11yKeyProbeStageEvent(event(18, 'keyDown', true, true, 2));
  assert.equal(posts[2][1], 'keyprobe-stage-down|18|2|1|1|0');
});

test('Probe deactivation and deadline both unregister without persistent observation', () => {
  const {ui, actions} = probeManager();
  ui.A11yKeyProbeOn();
  ui.A11yKeyProbeTick({type: 'deactivate'});
  assert.equal(actions.length, 0);
  ui.A11yKeyProbeOn();
  ui.mA11yKeyProbeUntil = 9999;
  ui.A11yKeyProbeTick({type: 'enterFrame'});
  assert.equal(actions.length, 0);
  assert.equal(ui.A11yKeyProbeValid(), false);
});
console.log(passed + ' Flash navigation fixture checks passed (not in-game verification).');
