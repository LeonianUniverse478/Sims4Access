'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(path.join(__dirname,'../flash/extra-classes/ControlPanel.as'),'utf8');
const match=/public function A11yNativeFloorQuery\(([^)]*)\)\s*:\s*void\s*\{/.exec(src);assert(match);
let at=match.index+match[0].length,end=at,depth=1;
while(depth){if(src[end]==='{')depth++;if(src[end]==='}')depth--;end++;}
const strip=s=>s.replace(/:\s*(?:Object|String|Number|Error|int)\b/g,'');
let count=0;
function fixture(info={curLevel:1,minLevel:-2,maxLevel:4}){
 const calls=[],ui={mA11yFloorQuerySequence:0,mGameState:2},flags={IsBetweenStates:false};
 const runtime={GameStates:{BUILD:2},GameStateFlags:flags,Number,String,isFinite,int:Math.trunc,
 CommunicationManager:{CallGameService(name,data){calls.push([name,data]);if(name==='BBGetCurrentZoneId')return '18446744073709551600';if(name==='BBGetLevelInfo')return info;}}};
 ui.query=vm.runInNewContext('(function('+strip(match[1])+'){'+strip(src.slice(at,end-1))+'})',runtime).bind(ui);
 return {ui,calls,flags};
}
function reply(f){return f.calls.filter(([n])=>n==='PostServerCommand').pop()[1];}
function test(name,fn){fn();count++;console.log('PASS '+name);}
test('native level, bounds and exact zone are returned without mutating game state',()=>{
 const f=fixture();f.ui.query();const r=reply(f);assert.equal(r.command,'a11y.floor_native');assert.deepEqual(Array.from(r.commandArgs),['18446744073709551600',1,'ok',1,-2,4]);
 assert(f.calls.every(([n])=>['BBGetLevelInfo','BBGetCurrentZoneId','PostServerCommand'].includes(n)));
});
test('sequence increases once per query',()=>{const f=fixture();f.ui.query();f.ui.query();assert.equal(reply(f).commandArgs[1],2);});
test('outside Build mode returns unavailable without querying level data',()=>{const f=fixture();f.ui.mGameState=1;f.ui.query();assert.equal(reply(f).commandArgs[2],'unavailable');assert(!f.calls.some(([n])=>n==='BBGetLevelInfo'));});
test('transition guard avoids querying changing world',()=>{const f=fixture();f.flags.IsBetweenStates=true;f.ui.query();assert.equal(reply(f).commandArgs[2],'unavailable');});
test('missing, fractional, boolean and inconsistent values are never floor zero',()=>{
 for(const data of [null,{}, {curLevel:false,minLevel:0,maxLevel:4},{curLevel:1.5,minLevel:0,maxLevel:4},{curLevel:2,minLevel:3,maxLevel:4},{curLevel:NaN,minLevel:0,maxLevel:4}]){const f=fixture(data);f.ui.query();assert.equal(reply(f).commandArgs[2],'unavailable');}
});
test('single native listener and no native floor setter or cursor injection',()=>{
 assert.equal((src.match(/AddMessageListener\("A11yNativeFloorQuery"/g)||[]).length,1);
 const body=src.slice(at,end);for(const forbidden of ['BBSetLevel','keybd_event','SetVirtualCursorPosition','SendVirtualCursorClick'])assert(!body.includes(forbidden));
});
console.log(count+' native floor bridge checks passed (native service mocked).');
