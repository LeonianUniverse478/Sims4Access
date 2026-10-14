'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObjectContainer|DisplayObject|Rectangle|String|Object|Boolean|Number|Array|Error|int)\b/g,'').replace(/\s+as\s+(DisplayObjectContainer|DisplayObject)\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,at-1))+'})',{getQualifiedClassName:o=>o.kind||'',DisplayObjectContainer:function(){}});
}
const kind='widgets.GameEntry.WorldSelection.SeasonSelect::SeasonSelectContainer';
function fixture(){
 const scope={kind,visible:true,alpha:1,stage:{}};
 for(const name of ['btnSpring','btnSummer','btnFall','btnWinter','btnConfirm'])scope[name]={name,parent:scope,visible:true,alpha:1,stage:scope.stage,mouseEnabled:true,enabled:name!=='btnConfirm'};
 const world={mcSeasonSelection:scope};const clicks=[];
 const ui={A11yLoadedWidget:name=>name==='GameEntryWorldSelection'?world:null,A11yIsLive:o=>!!o&&o.stage&&o.visible&&o.alpha>.01,A11yAnnounceDisplay:()=>{},mTooltipsLayer:null};
 ui.A11ySortBounds=o=>o.getBounds(o.stage);
 for(const name of ['A11ySeasonScope','A11ySeasonButton','A11ySeasonActivate','A11ySeasonBounds','A11yCollectFocusables'])ui[name]=method(name);
 ui.A11yClickControl=o=>{if(!ui.A11yIsLive(o)||!o.enabled||!o.mouseEnabled)return false;clicks.push(o.name);if(o!==scope.btnConfirm)scope.btnConfirm.enabled=true;else scope.btnConfirm.mouseEnabled=false;return true;};
 return {ui,scope,world,clicks};
}
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}
test('Season scope narrows to native selector',()=>{const f=fixture();assert.strictEqual(f.ui.A11ySeasonScope(),f.scope);});
test('Absent expansion leaves other menus alone',()=>{const f=fixture();delete f.world.mcSeasonSelection;assert.strictEqual(f.ui.A11ySeasonScope(),null);});
test('Invisible controls during transitions never own input',()=>{const f=fixture();f.scope.btnSpring.alpha=0;assert.strictEqual(f.ui.A11ySeasonScope(),null);});
test('Closing selector relinquishes ownership immediately',()=>{const f=fixture();f.scope.btnConfirm.mouseEnabled=false;assert.strictEqual(f.ui.A11ySeasonScope(),null);});
test('Only four seasons enter traversal, in visual order',()=>{const f=fixture(),out=[];f.ui.A11yCollectFocusables(f.scope,out,0);assert.deepStrictEqual(out.map(o=>o.name),['btnSpring','btnSummer','btnFall','btnWinter']);});
test('Enter selects exact season then uses native confirmation once',()=>{for(const n of ['btnSpring','btnSummer','btnFall','btnWinter']){const f=fixture();assert(f.ui.A11ySeasonActivate(f.scope[n],true));assert.deepStrictEqual(f.clicks,[n,'btnConfirm']);f.ui.A11ySeasonActivate(f.scope[n],true);assert.equal(f.clicks.length,2);}});
test('Space selects without committing',()=>{const f=fixture();f.ui.A11ySeasonActivate(f.scope.btnWinter,false);assert.deepStrictEqual(f.clicks,['btnWinter']);});
test('Disabled choice cannot confirm a previously selected season',()=>{const f=fixture();f.scope.btnConfirm.enabled=true;f.scope.btnWinter.enabled=false;f.ui.A11ySeasonActivate(f.scope.btnWinter,true);assert.equal(f.clicks.length,0);});
test('Hidden stale choice and unrelated controls do not activate',()=>{const f=fixture();f.scope.btnWinter.visible=false;f.ui.A11ySeasonActivate(f.scope.btnWinter,true);assert.equal(f.clicks.length,0);assert.equal(f.ui.A11ySeasonActivate({name:'btnWinter',parent:{kind:'Other'}},true),false);});
test('Ring follows visible name instead of hidden description below it',()=>{const f=fixture();f.scope.btnWinter.getBounds=()=>({top:100,bottom:700});f.scope.btnWinter.txtName={visible:true,alpha:1,stage:{},getBounds:()=>({bottom:420})};assert.equal(f.ui.A11ySeasonBounds(f.scope.btnWinter).bottom,428);});
test('Card border stays above visible description text',()=>{const f=fixture(),b=f.scope.btnWinter;b.getBounds=()=>({top:100,bottom:700});b.txtName={visible:true,alpha:1,stage:{},getBounds:()=>({top:390,bottom:420})};b.mcDescription={txtDescription:{visible:true,alpha:1,stage:{},getBounds:()=>({top:422,bottom:600})}};assert.equal(f.ui.A11ySeasonBounds(b).bottom,418);});
test('Hidden or animated description cannot collapse card',()=>{for(const top of [0,380]){const f=fixture(),b=f.scope.btnWinter;b.getBounds=()=>({top:100,bottom:700});b.txtName={visible:true,alpha:1,stage:{},getBounds:()=>({top:390,bottom:420})};b.mcDescription={txtDescription:{visible:true,alpha:1,stage:{},getBounds:()=>({top,bottom:600})}};assert.equal(f.ui.A11ySeasonBounds(b).bottom,428);b.mcDescription.txtDescription.visible=false;assert.equal(f.ui.A11ySeasonBounds(b).bottom,428);}});
console.log(count+' season checks passed (source fixtures; live checks required).');
