'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
class DisplayObjectContainer { contains(o) { return o === this; } }
class TextField {}
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObjectContainer|DisplayObject|TextField|Event|String|Object|Boolean|Number|Array|Error|int)\b/g,'').replace(/\s+as\s+DisplayObject\b/g,'').replace(/\bis\s+(DisplayObjectContainer|TextField)\b/g,'instanceof $1');
 return vm.runInNewContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,at-1))+'})',{getQualifiedClassName:o=>o.kind||'Widget',DisplayObjectContainer,TextField,getTimer:()=>1000,CommunicationManager:{CallUIService:()=>true}});
}
function fixture(mode){
 const hud={name:mode,kind:'HUD'}, dialog={name:'dialog'}, pie={name:'pie',mcMenu:{}}, dropdown={name:'dropdown'};
 const posts=[];
 const ctx={A11yGuideFrame:()=>{}, // the guided New Game has its own suite (test_guided_new_game.js)
  mA11yHudMode:1,mA11yKeyboard:true,mA11yHudBrowsing:mode==='hud-browsing',mA11yScopeHistory:[],
   mA11yDialogManager:{IsInstantiated:()=>true,GetCurrentRequest:()=>mode==='dialog'?{dialog}:null},
   mA11yStatusScope:mode==='status'?{}:null,mTooltipsLayer:{stage:{focus:null}},
   A11yWorldHudMode:()=>1,A11yTopModalWidget:()=>mode==='picker'?dialog:null,
   A11yOpenHud:()=>['phone-alert','phone-panel','needs'].includes(mode)?hud:null,
   A11yLoadedWidget:n=>mode==='pie'&&n==='PieMenu'?pie:null,
   A11yIsLive:o=>!!o,A11yIsAbove:()=>true,A11yIsInside:()=>false,
   A11ySeasonScope:()=>null,A11yCASStoryScope:()=>null,A11yFilterPopup:()=>null,
   A11yCurrentDropdown:()=>mode==='dropdown'?dropdown:null,A11yFindDropdownExtension:()=>null,
   A11yFocusHover:()=>{},A11yFocusInto:()=>{},A11yClearFocus:()=>{},A11yCancelIndex:()=>{},A11yClearRing:()=>{},
   A11yFocusSettled:()=>{},A11yBuildFrame:()=>{},A11yPhoneFrame:()=>{},A11yFollowCASInput:()=>{},
   A11yScannerOwner:()=>false,A11yFirstPersonState:()=>false,A11yPostToPython:(c,s)=>posts.push([c,decodeURIComponent(s)])};
 ctx.A11yPhoneBlocking=method('A11yPhoneBlocking');ctx.A11yIsModalScope=method('A11yIsModalScope');
 if(mode==='hud-browsing')ctx.mA11yScope=ctx.mTooltipsLayer.stage;
 if(mode==='status')ctx.mA11yScope=ctx.mA11yStatusScope;
 return {ctx,posts};
}
let checks=0;
for(const mode of ['phone-alert','phone-panel','needs','hud-browsing','status','dialog','picker','pie','dropdown','world']){
 const {ctx,posts}=fixture(mode);method('A11yModalFrame').call(ctx);
 const blocking=['dialog','picker','pie','dropdown'].includes(mode)?'1':'0';
 const state=mode==='world'?'00':'10';
 assert(posts.some(p=>p[0]==='a11y.modalstate'&&p[1]===state),mode+' owner report');
 assert(posts.some(p=>p[0]==='a11y.blocking'&&p[1]===blocking),mode+' blocking report');
 assert(posts.some(p=>p[0]==='a11y.context_enc'&&p[1].endsWith(':'+state+blocking)),mode+' atomic context');
 checks++;
}
// A managed dialog behind a HUD must still prohibit changing the active Sim.
const {ctx}=fixture('needs');ctx.mA11yManagedDialog={};ctx.mA11yHudRoot={};
assert.strictEqual(ctx.A11yPhoneBlocking(ctx.mA11yHudRoot),true);checks++;
for(const [clock, expected] of [
 [null,''],
 [{txtGameTime:{text:'Tuesday 2:45 PM'},txtTimeSpeedName:{visible:false,text:'Paused'}},'Tuesday 2:45 PM'],
 [{txtGameTime:{text:'Tuesday 2:45 PM'},txtTimeSpeedName:{visible:true,text:'Paused'}},'Tuesday 2:45 PM. Paused'],
 [{txtGameTime:{text:'Mardi 14:45'},txtTimeSpeedName:{visible:true,text:'En pause'}},'Mardi 14:45. En pause'],
 [{txtGameTime:{text:''},txtTimeSpeedName:{visible:true,text:'Paused'}},''],
 [{txtGameTime:{text:"Samedi (l'heure)!"},txtTimeSpeedName:{visible:false,text:''}},"Samedi (l'heure)!"]
]) {
 const posts=[];
 method('A11yClock').call({A11yLoadedWidget:()=>clock,A11yIsLive:o=>!!o,A11yPostToPython:(c,p)=>posts.push([c,decodeURIComponent(p)])});
 assert.strictEqual(JSON.stringify(posts),JSON.stringify([['a11y.clock_enc','clock:'+expected]]));checks++;
}
// An alert changing into a dialog retains navigation ownership (10):
// the independent blocking report must still change, even without modalstate.
const transition=fixture('phone-alert');
const frame=method('A11yModalFrame');frame.call(transition.ctx);transition.posts.length=0;
transition.ctx.A11yOpenHud=()=>null;
transition.ctx.mA11yDialogManager.GetCurrentRequest=()=>({dialog:{name:'dialog'}});
frame.call(transition.ctx);
assert(transition.posts.some(p=>p[0]==='a11y.context_enc'&&p[1].endsWith(':101')));
assert(transition.posts.some(p=>p[0]==='a11y.blocking'&&p[1]==='1'));
assert(!transition.posts.some(p=>p[0]==='a11y.modalstate'));checks++;
transition.posts.length=0;frame.call(transition.ctx);
assert.strictEqual(transition.posts.length,0);checks++;
for(const field of ['mA11yBlockingReported','mA11yModalReported','mA11yOwnerReported'])transition.ctx[field]='';
frame.call(transition.ctx);
assert.strictEqual(transition.posts.filter(p=>['a11y.context_enc','a11y.modalstate','a11y.blocking'].includes(p[0])).length,3);checks++;
console.log(checks+' phone owner and clock checks passed');
