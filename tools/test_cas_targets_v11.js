'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObject|Rectangle|Object|Boolean|Error)\b/g,'').replace(/\s+as\s+DisplayObject\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,at-1))+'})',{getQualifiedClassName:o=>o.kind,MouseEvent:{MOUSE_DOWN:'down',MOUSE_UP:'up',CLICK:'click'}});
}
function fixture(){
 const owner={kind:'widgets.CAS.NameField::CASNameFieldMain',visible:true,alpha:1,stage:{}};
 const label={parent:owner,visible:true,alpha:1,stage:owner.stage},button={parent:owner,visible:true,alpha:0,enabled:true,mouseEnabled:true,stage:owner.stage};
 owner.txtFullNameDisplay=label;owner.btnTextEffect=button;
 const calls=[],ui={A11yCASNameLabel:method('A11yCASNameLabel'),activate:method('A11yActivateCASName'),A11yIsLive:item=>{if(!item||!item.stage)return false;for(let n=item;n;n=n.parent)if(!n.visible||n.alpha<=.01)return false;return true;},A11ySafeDispatch:(target,event)=>calls.push([target,event])};
 return {owner,label,button,calls,ui};
}
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}
test('Transparent CAS button resolves to visible label and activates EA mouse sequence once',()=>{const f=fixture();assert.strictEqual(f.ui.A11yCASNameLabel(f.button),f.label);assert(f.ui.activate(f.label));assert.deepStrictEqual(f.calls.map(x=>x[1]),['down','up','click']);assert(f.calls.every(x=>x[0]===f.button));assert.strictEqual(f.button.alpha,0);assert.strictEqual(f.ui.mA11yActivating,false);});
test('Hovered overlay remains the same semantic target',()=>{const f=fixture();f.button.alpha=1;assert.strictEqual(f.ui.A11yCASNameLabel(f.button),f.label);});
test('Hidden or detached labels never activate',()=>{for(const mutate of [f=>f.label.visible=false,f=>f.owner.visible=false,f=>f.owner.alpha=0,f=>f.label.stage=null]){const f=fixture();mutate(f);assert.strictEqual(f.ui.activate(f.label),false);assert.strictEqual(f.calls.length,0);}});
test('Expanded, disabled, mouse-disabled and detached buttons never activate',()=>{for(const mutate of [f=>f.button.visible=false,f=>f.button.enabled=false,f=>f.button.mouseEnabled=false,f=>f.button.parent=null]){const f=fixture();mutate(f);assert.strictEqual(f.ui.activate(f.label),false);assert.strictEqual(f.calls.length,0);}});
test('Unrelated labels and controls with similar names remain untouched',()=>{const f=fixture();assert.strictEqual(f.ui.A11yCASNameLabel({parent:f.owner}),null);f.owner.kind='other::CASNameFieldMain';assert.strictEqual(f.ui.activate(f.label),false);assert.strictEqual(f.ui.activate(null),false);});
test('Dispatch failure clears synthetic activation state',()=>{const f=fixture();f.ui.A11ySafeDispatch=()=>{throw Error('removed');};assert.strictEqual(f.ui.activate(f.label),false);assert.strictEqual(f.ui.mA11yActivating,false);});


const intersects=method('A11yIntersectsStage');
const stage={stageWidth:1693,stageHeight:1030};
function item(x,y,w,h){return {stage,getBounds:()=>({left:x,top:y,right:x+w,bottom:y+h})};}
for(const [name,rect,want] of [
 ['visible Save clipped above',[1459,-2,58,50],true],['visible Share clipped above',[1510,-7,69,76],true],['Identity',[8,6,61,61],true],
 ['offstage Help',[1887,53,29,28],false],['offstage Floors',[1810,59,24,35],false],['offstage Scenario',[1847,64,30,31],false],
 ['left overlap',[-10,20,20,20],true],['top overlap',[20,-10,20,20],true],['bottom overlap',[20,1020,20,20],true],
 ['left edge no overlap',[-20,20,20,20],false],['top edge no overlap',[20,-20,20,20],false],['right edge no overlap',[1693,20,20,20],false],['below stage',[20,1030,20,20],false]
]){assert.strictEqual(intersects(item(...rect)),want,name);count++;}
assert.strictEqual(intersects(null),false);assert.strictEqual(intersects({stage:null}),false);assert.strictEqual(intersects({stage,getBounds:()=>{throw Error('removed')}}),false);
count+=3;
const reveal=method('A11yCanRevealOnStage');
const revealUI={A11yIntersectsStage:intersects,A11yIsLive:view=>view.live!==false};
for(const [viewKey,sliderKey] of [['mScrollerView','mSlider'],['mcView','mcSlider'],['mcScheduleView','mcScheduleSlider']]){
 function scroller(){const mask=item(10,10,100,100);mask.visible=false;return {[viewKey]:{mcMask:mask,live:true},[sliderKey]:{}};}
 test(viewKey+' retains offstage rows with a hidden mask onstage',()=>{const parent=scroller();assert.strictEqual(reveal.call(revealUI,{parent}),true);});
 test(viewKey+' rejects offstage viewport',()=>{const parent=scroller();parent[viewKey].mcMask=item(1800,0,100,100);assert.strictEqual(reveal.call(revealUI,{parent}),false);});
 test(viewKey+' rejects hidden view or missing slider',()=>{const parent=scroller();parent[viewKey].live=false;assert.strictEqual(reveal.call(revealUI,{parent}),false);parent[viewKey].live=true;parent[sliderKey]=null;assert.strictEqual(reveal.call(revealUI,{parent}),false);});
 test(viewKey+' supports nested rows',()=>{assert.strictEqual(reveal.call(revealUI,{parent:{parent:scroller()}}),true);});
}
test('Unrelated ancestors do not grant an offstage exception',()=>{assert.strictEqual(reveal.call(revealUI,{parent:{parent:{}}}),false);assert.strictEqual(reveal.call(revealUI,null),false);});
test('Removed scroller fails closed',()=>{const parent={mSlider:{},get mScrollerView(){throw Error('removed');}};assert.strictEqual(reveal.call(revealUI,{parent}),false);});
console.log(count+' CAS name and stage checks passed');
