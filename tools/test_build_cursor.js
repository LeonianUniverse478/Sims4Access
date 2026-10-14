'use strict';
// The Build cursor in TooltipManager: A11yBuildGridOwner decides whether plain
// keys belong to it (Build mode, keyboard on, nothing modal, not typing, no
// pixel cursor); A11yGuardValid consumes its keys only then, and never claims
// the new keys (Page Up/Down, Home, Delete, 1-6, R) for anything else;
// A11yBuildGridOnMsg releases an owning catalog silently. Logic only.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
class DisplayObjectContainer { constructor(n){this.name=n;} contains(o){return o===this;} }
class TextField {}
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObjectContainer|DisplayObject|TextField|Event|String|Object|Boolean|Number|Array|Error|int)\b/g,'').replace(/\s+as\s+DisplayObject\b/g,'').replace(/\bis\s+(DisplayObjectContainer|TextField)\b/g,'instanceof $1');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*(null|true)/g,'')+'){'+strip(source.slice(start,at-1))+'})',
  {getQualifiedClassName:o=>o&&o.kind||'Widget',DisplayObjectContainer,TextField,getTimer:()=>1000});
}
function fixture(over){
 const posts=[];
 const catalog=new DisplayObjectContainer('catalog');
 const w=Object.assign({hud:2,editing:false},over||{});
 const ctx={mA11yBuildGridOn:true,mA11yKeyboard:true,mA11yKeyboardLease:5000,mA11yStartupActive:false,mA11yScannerMode:false,
  mA11yBuildCursor:false,mA11yHudBrowsing:false,mA11yStatusScope:null,mA11yActiveModalRoot:null,mA11yScope:null,mA11yPendingScope:null,
  mA11yGuardHeld:{},mA11yScopeHistory:[],mA11yCatalogReleased:null,mA11yFocused:null,
  A11yWorldHudMode:()=>w.hud,A11yEditing:()=>w.editing,A11yIsLive:o=>!!o,A11yModalFrame:()=>{},
  A11yLauncherNavigation:()=>null,A11yLoadedWidget:n=>n==='BuildBuyProductCatalog'?catalog:null,
  A11yCancelIndex:()=>{},A11yClearFocus:()=>{},A11yPostToPython:(c,p)=>posts.push([c,p])};
 for(const n of ['A11yBuildGridOwner','A11yGuardValid','A11yIsModalScope','A11yReleaseBuildCatalog','A11yIsBuildBuy','A11yBuildCatalogOwner','A11yBuildGridOnMsg','A11yBuildGridOffMsg'])ctx[n]=method(n);
 return {ctx,w,catalog,posts};
}
let checks=0;
const cursorKeys=[8,13,27,32,33,34,36,37,38,39,40,46,49,50,51,52,53,54,82];
const newKeys=[33,34,36,46,49,50,51,52,53,54,82];
{const f=fixture();assert.strictEqual(f.ctx.A11yBuildGridOwner(),true);
 for(const k of cursorKeys)assert.strictEqual(f.ctx.A11yGuardValid(k),true,'cursor key '+k);checks++;}
for(const [label,change] of [
 ['off',c=>{c.ctx.mA11yBuildGridOn=false;}],['Live mode',c=>{c.w.hud=1;}],['typing',c=>{c.w.editing=true;}],
 ['a dialog',c=>{c.ctx.mA11yActiveModalRoot=new DisplayObjectContainer('dialog');}],
 ['pixel cursor',c=>{c.ctx.mA11yBuildCursor=true;}],['HUD browsing',c=>{c.ctx.mA11yHudBrowsing=true;}],
 ['keyboard lease lapsed',c=>{c.ctx.mA11yKeyboardLease=0;}],['startup',c=>{c.ctx.mA11yStartupActive=true;}]]){
 const f=fixture();change(f);
 assert.strictEqual(f.ctx.A11yBuildGridOwner(),false,label);
 for(const k of newKeys)assert.strictEqual(f.ctx.A11yGuardValid(k),false,label+': new key '+k+' stays the game\'s');
 checks++;
}
// A dialog still owns Enter/Escape/arrows through the ordinary rules.
{const f=fixture();f.ctx.mA11yActiveModalRoot=new DisplayObjectContainer('dialog');
 for(const k of [13,27,38])assert.strictEqual(f.ctx.A11yGuardValid(k),true,'dialog key '+k);checks++;}
// Nothing owning anything: the world keeps its arrows and Enter.
{const f=fixture();f.ctx.mA11yBuildGridOn=false;for(const k of [13,32,37])assert.strictEqual(f.ctx.A11yGuardValid(k),false);checks++;}
// Turning the cursor on releases an owning catalog without announcing it.
{const f=fixture();f.ctx.mA11yBuildGridOn=false;f.ctx.mA11yActiveModalRoot=f.catalog;
 f.ctx.A11yBuildGridOnMsg();
 assert.strictEqual(f.ctx.mA11yBuildGridOn,true);assert.strictEqual(f.ctx.mA11yCatalogReleased,f.catalog);
 assert.strictEqual(f.ctx.mA11yActiveModalRoot,null);assert.deepStrictEqual(f.posts,[],'silent');
 f.ctx.A11yBuildGridOffMsg();assert.strictEqual(f.ctx.mA11yBuildGridOn,false);checks++;}
// Ctrl+Alt+B while Tab-browsing inside the catalog also releases it, silently.
{const f=fixture();f.ctx.mA11yBuildGridOn=false;const cell=new DisplayObjectContainer('cell');cell.parent=f.catalog;
 f.ctx.mA11yHudBrowsing=true;f.ctx.mA11yScope={};f.ctx.mA11yFocused=cell;
 f.ctx.A11yBuildGridOnMsg();
 assert.strictEqual(f.ctx.mA11yHudBrowsing,false);assert.strictEqual(f.ctx.mA11yCatalogReleased,f.catalog);
 assert.strictEqual(f.ctx.A11yBuildGridOwner(),true,'the cursor owns the keys now');assert.deepStrictEqual(f.posts,[]);checks++;}
// Installed guards include the new keys, Shift for R, and Build mode exit clears the flag.
assert(/var keys:Array = \[8,9,13,27,32,37,38,39,40,78,33,34,36,46,49,50,51,52,53,54,82\];/.test(source));
assert(/keys\[i\] == 9 \|\| keys\[i\] == 82 \? 2 : 1/.test(source));
assert(/this\.mA11yCatalogReleased = null;\r?\n\s*this\.mA11yBuildGridOn = false;/.test(source));
assert(/"a11y\.buildgridowner",buildGridState/.test(source));checks++;
const added=source.slice(source.indexOf('public function A11yBuildGridOwner'),source.indexOf('public function A11yReturnToCatalog'));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' Build cursor template checks passed');
