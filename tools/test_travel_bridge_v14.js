'use strict';
// Execute the actual AS bridge methods with the native clock/message surface stubbed.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name,context){
 const sig=new RegExp('public (?:static )?function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
 assert(sig,name);let start=sig.index+sig[0].length,end=start,depth=1;
 while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
 const strip=s=>s.replace(/:\s*(String|Array|int|Boolean)\b(?!\s*\()/g,'');
 return vm.runInContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,end-1))+'})',context);
}
let now=10000,messages=[],count=0;
const ctx=vm.createContext({getTimer:()=>now,int:Number,String,
 sInstance:{mA11yKeyboard:true,mA11yKeyboardLease:11000},
 sA11yTravelLease:0,sA11yTravelLeaseTime:0,sA11yTravelList:false,
 CommunicationManager:{SendUIMessage:(name,data)=>messages.push({name,data})}});
const parse=method('A11yHandleEncoded',ctx),ready=method('A11yTravelCanRoute',ctx);
function test(name,fn){fn();count++;console.log('PASS '+name);}
test('Routing defaults off until setting and readiness both arrive',()=>{assert(!ready());parse('A11y|travellist|on');assert(!ready());parse('A11y|travelready|7');assert(ready());});
test('Heartbeat retains epoch and refreshes age',()=>{now=10500;parse('A11y|travelready|7');assert.equal(ctx.sA11yTravelLease,7);assert.equal(ctx.sA11yTravelLeaseTime,10500);assert.equal(messages.at(-1).data.epoch,7);});
test('Setting off prevents routing immediately',()=>{parse('A11y|travellist|off');assert(!ready());parse('A11y|travellist|on');assert(ready());});
test('Keyboard off and dead keyboard lease prevent routing',()=>{ctx.sInstance.mA11yKeyboard=false;assert(!ready());ctx.sInstance.mA11yKeyboard=true;now=11001;assert(!ready());ctx.sInstance.mA11yKeyboardLease=20000;assert(ready());});
test('Stale travel heartbeat and invalid clock age prevent routing',()=>{now=15501;assert(!ready());now=10499;assert(!ready());now=10500;assert(ready());});
test('Stop heartbeat prevents routing immediately',()=>{parse('A11y|travelready|0');assert(!ready());});
test('Results preserve epoch and request identity including cancellation',()=>{parse('A11y|travelresult|7|12|refused|cancelled');const m=messages.at(-1);assert.equal(m.name,'A11yTravelResult');assert.equal(m.data.epoch,7);assert.equal(m.data.request,12);assert.equal(m.data.reason,'cancelled');});
test('Malformed short result does not settle a request',()=>{const n=messages.length;parse('A11y|travelresult|12|ok');assert.equal(messages.length,n);});
console.log(count+' travel bridge checks passed');
