'use strict';
// ControlPanel M route state machine, run from the actual extra-classes/ControlPanel.as bodies.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/extra-classes/ControlPanel.as'),'utf8');
function body(name){
 const sig=new RegExp('protected function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,'missing '+name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 return {params:sig[1],text:source.slice(start,at-1)};
}
const strip=s=>s.replace(/:\s*(Object|int|Boolean|Error|String)\b/g,'').replace(/\bvar\s+(\w+)\s*=/g,'var $1 =');
function make(name,ctx){const b=body(name);return vm.runInNewContext('(function('+strip(b.params)+'){'+strip(b.text)+'})',ctx);}
function panel(opts){
 const o=Object.assign({canRoute:true,lease:5,guardsOk:true,throwOn:null},opts||{});
 const posted=[];
 const ctx={
  int:x=>Math.trunc(Number(x))||0, getTimer:()=>ctx.now, getDefinitionByName:()=>({A11yTravelCanRoute:()=>{if(o.throwOn==='canroute')throw new Error('x');return o.canRoute;},sA11yTravelLease:o.lease}),
  CommunicationManager:{CallGameService:(svc,arg)=>{if(o.throwOn===arg.command)throw new Error('post');posted.push(arg);}},
  GameStates:{LOT_SELECT:9}, GameStateFlags:{IsBetweenStates:!o.guardsOk}, GameplayStateData:{HasSims:true},
  now:1000,
 };
 const self={mGameState:1,mbIsSaveLoadLocked:false,mA11yTravelEpoch:0,mA11yTravelRequest:0,mA11yTravelPending:0,mA11yTravelPendingEpoch:0,mA11yTravelSent:0,mA11yTravelCancelSent:false};
 for(const n of ['A11yRouteTravel','A11yCancelTravel','A11yClearTravelPending','A11yHandleTravelReady','A11yHandleTravelResult'])self[n]=make(n,ctx);
 self.ctx=ctx;self.posted=posted;
 return self;
}
const same=(a,b)=>assert.strictEqual(JSON.stringify(a),JSON.stringify(b));   // vm objects are not reference-equal
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}

test('No lease: native map, nothing posted',()=>{const p=panel({canRoute:false});assert.strictEqual(p.A11yRouteTravel(),false);same(p.posted,[]);assert.strictEqual(p.mA11yTravelPending,0);});
test('Inner guards fail: native map even with a lease',()=>{const p=panel({guardsOk:false});assert.strictEqual(p.A11yRouteTravel(),false);same(p.posted,[]);});
test('Fresh lease dispatches one request bound to the epoch',()=>{const p=panel();assert.strictEqual(p.A11yRouteTravel(),true);same(p.posted,[{command:'a11y.travel',commandArgs:[5,1]}]);assert.strictEqual(p.mA11yTravelPending,1);assert.strictEqual(p.mA11yTravelPendingEpoch,5);});
test('Repeated M while pending is swallowed without a second dispatch, even without a lease',()=>{const p=panel();p.A11yRouteTravel();p.ctx.now+=500;assert.strictEqual(p.A11yRouteTravel(),true);p.ctx.now+=500;assert.strictEqual(p.A11yRouteTravel(),true);assert.strictEqual(p.posted.length,1);});
test('After 3 s a single cancel is posted with the original epoch and the press stays routed',()=>{const p=panel();p.A11yRouteTravel();p.ctx.now+=3500;assert.strictEqual(p.A11yRouteTravel(),true);p.ctx.now+=1000;assert.strictEqual(p.A11yRouteTravel(),true);same(p.posted.slice(1),[{command:'a11y.travel_cancel',commandArgs:[1,5]}]);assert.strictEqual(p.mA11yTravelPending,1);});
test('Result for the pending epoch and request clears it; others do not',()=>{const p=panel();p.A11yRouteTravel();p.A11yHandleTravelResult({epoch:4,request:1,outcome:'ok'});assert.strictEqual(p.mA11yTravelPending,1);p.A11yHandleTravelResult({epoch:5,request:2,outcome:'ok'});assert.strictEqual(p.mA11yTravelPending,1);p.A11yHandleTravelResult({epoch:5,request:1,outcome:'refused',reason:'cancelled'});assert.strictEqual(p.mA11yTravelPending,0);assert.strictEqual(p.mA11yTravelCancelSent,false);});
test('Cancel acknowledgement releases M and the next press dispatches a new request',()=>{const p=panel();p.A11yRouteTravel();p.ctx.now+=3500;p.A11yRouteTravel();p.A11yHandleTravelResult({epoch:5,request:1,outcome:'refused',reason:'cancelled'});assert.strictEqual(p.A11yRouteTravel(),true);same(p.posted[p.posted.length-1],{command:'a11y.travel',commandArgs:[5,2]});});
test('A ready message with a new epoch clears a pending request; the same epoch keeps it',()=>{const p=panel();p.A11yRouteTravel();p.A11yHandleTravelReady({epoch:5});assert.strictEqual(p.mA11yTravelPending,1);p.A11yHandleTravelReady({epoch:6});assert.strictEqual(p.mA11yTravelPending,0);});
test('Exception before the dispatch attempt gives the native map; after it the press stays routed',()=>{const a=panel({throwOn:'canroute'});assert.strictEqual(a.A11yRouteTravel(),false);assert.strictEqual(a.mA11yTravelPending,0);const b=panel({throwOn:'a11y.travel'});assert.strictEqual(b.A11yRouteTravel(),true);assert.strictEqual(b.mA11yTravelPending,1);});
test('Native map branch is only reached through the route check',()=>{assert(/else if\(!this\.A11yRouteTravel\(\)\)\s*\{\s*this\.ChangeGameStateToNeighborhood\(TransitionScreenMode\.LIVE_TO_NHD_MAP_TRAVEL\);/.test(source));assert(!/\+\+/.test(source),'no increment operators');});
console.log(count+' ControlPanel route checks passed (source bodies, not in-game verification)');
