'use strict';
// Execute the actual encoded pick -> native pie callback -> interactions.choices
// chain. Native services are recorded only; this never interacts with a game.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const ttm = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
const pieSource = fs.readFileSync(path.join(__dirname, '../flash/extra-classes/PieMenuMain.as'), 'utf8');
function method(source, name, context) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(signature, name);
  let start = signature.index + signature[0].length, at = start, depth = 1;
  while (depth) { if (source[at] === '{') depth++; if (source[at] === '}') depth--; at++; }
  const strip = text => text.replace(/(\w)\s*:\s*(uint|int|Number|String|Object|Array|Boolean|Error|WorldPickResult)\b/g, '$1');
  return vm.runInContext('(function(' + strip(signature[1]) + '){' + strip(source.slice(start, at - 1)) + '})', context);
}
const sent = [], requests = [], hooks = [];
const context = vm.createContext({String, Number, Boolean, int: Math.trunc, uint: value => Number(value) >>> 0,
  getTimer: () => 10000, encodeURIComponent, decodeURIComponent,
  WorldPickResult: function() {}, sA11yPick: null, sA11yHooked: false,
  ExternalInterface: {available: true, addCallback: (name, fn) => hooks.push([name, fn])},
  CommunicationManager: {
    SendUIMessage(name, data) { sent.push([name, data]); if (name === 'A11yOpenPieMenu') pie.A11yOnOpenPieMenu(data); return true; },
    CallGameService(name, data) { requests.push([name, data]); }
  }});
const manager = {mA11yScannerMode: false, mA11yScannerOwnerReported: '1', mA11yScannerLiveReported: '1'};
for (const name of ['A11yInstallGameMessageHook', 'A11yOnGameMessage', 'A11yHandleEncoded']) {
  manager[name] = method(ttm, name, context);
}
let requestId = 10;
const pie = {isInventoryRequest: true, isCloseEvent: true, mbShiftOnPickup: true};
Object.defineProperty(pie, 'mLastInteractionRequestId', {get: () => requestId, set: value => {requestId = value >>> 0;}});
pie.A11yOnOpenPieMenu = method(pieSource, 'A11yOnOpenPieMenu', context);
let checks = 0;
assert(/AddMessageListener\("A11yOpenPieMenu",this\.A11yOnOpenPieMenu\)/.test(pieSource)); checks++;
manager.A11yInstallGameMessageHook();
assert.strictEqual(hooks[0][0], 'SendMessage'); assert.strictEqual(hooks[0][1], manager.A11yOnGameMessage); checks++;
const objectId = '18446744073709551615';
assert.strictEqual(hooks[0][1].call(manager, 'A11y|pick|' + objectId + '|1|77||1.25|2.5|-3.75|-1'), true);
assert.strictEqual(sent[0][0], 'A11yOpenPieMenu');
assert.strictEqual(requests[0][0], 'PostServerCommand');
assert.strictEqual(requests[0][1].command, 'interactions.choices');
assert.deepStrictEqual(Array.from(requests[0][1].commandArgs), [objectId,1,1.25,2.5,-3.75,77,-1,0,0,0,11,0,0,true]); checks++;
assert.strictEqual(pie.mPickResults.objectId, objectId);
assert.strictEqual(pie.isInventoryRequest, false); assert.strictEqual(pie.isCloseEvent, false); assert.strictEqual(pie.mbShiftOnPickup, false); checks++;
manager.A11yOnGameMessage('A11y|pick|12345678901234567|2|88|Ari|4|5|6|2');
assert.strictEqual(pie.mPickResults.simFirstName, 'Ari'); assert.strictEqual(pie.mPickResults.pickType, 2);
assert.strictEqual(requests[1][1].commandArgs[0], '12345678901234567'); checks++;
const before = requests.length;
manager.A11yOnGameMessage('A11y|pick|123'); assert.strictEqual(requests.length, before); checks++;
manager.A11yOnGameMessage('NativeGameMessage', {native: true}); assert.strictEqual(sent.at(-1)[0], 'NativeGameMessage'); checks++;
manager.A11yOnGameMessage('A11y|scannermode|on'); assert.strictEqual(manager.mA11yScannerMode, true);
assert.strictEqual(manager.mA11yScannerOwnerReported, ''); assert.strictEqual(manager.mA11yScannerLiveReported, '');
manager.A11yOnGameMessage('A11y|scannermode|invalid'); assert.strictEqual(manager.mA11yScannerMode, true);
manager.A11yOnGameMessage('A11y|scannermode|off'); assert.strictEqual(manager.mA11yScannerMode, false); checks++;
requestId = 0xffffffff;
manager.A11yOnGameMessage('A11y|pick|9|1|77||0|0|0|0');
assert.strictEqual(requestId, 1); assert.strictEqual(requests.at(-1)[1].commandArgs[10], 1); checks++;
manager.A11yOnGameMessage('A11y|pick|0|5|77||10.25|6.5|-4.125|2');
assert.deepStrictEqual(Array.from(requests.at(-1)[1].commandArgs), ['0',5,10.25,6.5,-4.125,77,2,0,0,0,2,0,0,true]);
assert.strictEqual(pie.mPickResults.pickType,5);checks++;
manager.A11yOnGameMessage('A11y|pick|18446744073709551615|11|0|Home Sim|1.5|3|-4|2');
assert.deepStrictEqual(Array.from(requests.at(-1)[1].commandArgs), ['18446744073709551615',11,1.5,3,-4,0,2,0,0,0,3,0,0,true]);
assert.strictEqual(pie.mPickResults.pickType,11);checks++;
console.log(checks + ' scanner pick bridge checks passed (native services mocked).');
