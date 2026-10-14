'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
function method(name) {
  const header = new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*void\\s*\\{').exec(source);
  assert(header, name);
  let start=header.index+header[0].length, end=start, depth=1;
  while(depth) { if(source[end]==='{') depth++; if(source[end]==='}') depth--; end++; }
  return vm.runInNewContext('(function(param1=null){'+source.slice(start,end-1)+'})');
}
let checks=0;
for (const [name, direction] of [['A11yMsgNext',1],['A11yMsgPrev',-1]]) {
  const invoke=method(name);
  for (const mode of ['closed','open','pending','closed-on-refresh']) {
    const calls=[];
    const owner={};
    const ctx={mA11yScope:mode==='open'||mode==='closed-on-refresh'?owner:null,
      mA11yPendingScope:mode==='pending'?owner:null,
      A11yModalFrame() { if(mode==='closed-on-refresh') this.mA11yScope=null; },
      A11yIsModalScope(scope) { return scope===owner; },
      A11yTabMove(dir) { calls.push(dir); }};
    invoke.call(ctx);
    assert.deepStrictEqual(calls, mode==='open'||mode==='pending'?[direction]:[],name+' '+mode);
    checks++;
  }
}
console.log(checks+' navigation owner checks passed');
