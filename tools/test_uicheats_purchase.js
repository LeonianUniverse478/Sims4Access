'use strict';
// Run generated compatibility click handlers without interacting with a game.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
let input = process.argv[2], temporary;
if (!input) {
  temporary = fs.mkdtempSync(path.join(require('os').tmpdir(), 's4-cart-test-'));
  input = path.join(temporary, 'cell.as');
  require('child_process').execFileSync('py', ['-3.7', path.join(__dirname, '../flash/prepare_uicheats_purchase.py'), input]);
}
const source = fs.readFileSync(input, 'utf8');
if (temporary) { fs.unlinkSync(input); fs.rmdirSync(temporary); }
let checks = 0;
for (const direction of ['Increase', 'Decrease']) {
  const header = 'protected function On' + direction + 'Click(param1:MouseEvent) : void';
  const index = source.indexOf(header); assert(index >= 0, header);
  let cursor = source.indexOf('{', index) + 1, start = cursor, depth = 1;
  while (depth) { if (source[cursor] === '{') depth++; if (source[cursor] === '}') depth--; cursor++; }
  const fn = vm.runInNewContext('(function(param1){' + source.slice(start, cursor - 1) + '})', {
    InputUtils: { IsRightMouseButton: event => event.right }
  });
  for (const right of [false, true]) {
    let count = 0;
    fn.call({[direction + 'Amount']() { count++; }}, {right});
    assert.strictEqual(count, right ? 10 : 1); checks++;
  }
}
assert(!source.includes('PushButtonEvent.CLICK'));
assert(source.includes('this.A11yQueueAmountAnnounce();'));
assert(source.includes('this.A11yHookSpinButtons();'));
console.log(checks + ' compatibility quantity click checks passed; narration hooks retained.');
