'use strict';
// Execute the actual AS3 narration method with EA-shaped data. This does not
// simulate Scaleform focus, occult tuning, or the game's placement/services.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(path.join(__dirname, '../flash/extra-classes/CommodityContainer.as'), 'utf8');
const start = source.indexOf('public function A11yMotiveText() : String');
assert(start >= 0);
let at = source.indexOf('{', start) + 1, begin = at, depth = 1;
while (depth) { if (source[at] === '{') depth++; if (source[at] === '}') depth--; at++; }
const code = source.slice(begin, at - 1).replace(/:(String|Number|Error)\b/g, '');
const traits = ['occult-trait'];
const fn = vm.runInNewContext('(function(){' + code + '})', {
  GameplayStateData: { AllTraitIds: traits }, Math, isFinite
});
let calls = 0;
function need(value, lo = -100, hi = 100) {
  return { Value: value, mCommodityData: {
    commodity_name: { toString() { throw Error('Generic name must not be read'); } },
    GetCommodityName(ids) { assert.strictEqual(ids, traits); calls++; return 'Thirst'; },
    min_value_tuning: lo, max_value_tuning: hi
  }};
}
assert.strictEqual(fn.call(need(0)), 'Thirst. 50%');
assert.strictEqual(fn.call(need(80, 0, 100)), 'Thirst. 80%');
assert.strictEqual(fn.call(need(-200)), 'Thirst. 0%');
assert.strictEqual(fn.call(need(200)), 'Thirst. 100%');
assert.strictEqual(fn.call(need(NaN)), 'Thirst');
assert.strictEqual(fn.call(need(Infinity)), 'Thirst');
assert.strictEqual(fn.call({mCommodityData: null}), '');
assert.strictEqual(calls, 6);
console.log('7 occult motive narration checks passed.');
