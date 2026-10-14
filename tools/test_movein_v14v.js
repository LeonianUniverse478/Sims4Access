'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObject|Rectangle|String|Object|Boolean|Number|Array|Error|int)\b/g,'').replace(/\s+as\s+(DisplayObject|Rectangle)\b/g,'').replace('for each(field in','for(field of');
 return vm.runInNewContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,at-1))+'})',{getQualifiedClassName:o=>o.kind||''});
}
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}
const bounds=method('A11ySortBounds'),quote=method('A11yMoveInQuote'),decoration=method('A11yKeyboardDecoration');
test('Non-actionable neighborhood tags never trap the lot Tab ring',()=>{
 const ui={A11yTextDecoration:()=>false,A11yDialogCloseButton:()=>false};
 assert.strictEqual(decoration.call(ui,{kind:'widgets.GameEntry.Neighborhood.controls::StreetTag',name:'tag'}),true);
 const street={mcLots:{}};street.btnStreetTag={kind:'WorldSpecificTag',name:'btnStreetTag',parent:street};
 assert.strictEqual(decoration.call(ui,street.btnStreetTag),true);
 assert.strictEqual(decoration.call(ui,{kind:'WorldSpecificLot',name:'lot',parent:street}),false);
 assert.strictEqual(decoration.call(ui,{kind:'Button',name:'btnConfirm',parent:{}}),false);
});
test('Native measured house bounds replace transparent image margins for lot types',()=>{
 for(const type of ['LotClip','MultiUnitLotClip','StreetTaggedLotClip']){
  const measured={x:400,y:300,width:110,height:90};
  const item={kind:'widgets.GameEntry.Neighborhood.controls::'+type,stage:{},mcTooltipDummy:{stage:{},alpha:0,getBounds:()=>measured},getBounds:()=>({width:800,height:500})};
  assert.strictEqual(bounds(item),measured);
 }
});
test('Unloaded or zero-sized lot anchors use normal bounds',()=>{
 const normal={width:80,height:50};const item={kind:'widgets.GameEntry.Neighborhood.controls::LotClip',getBounds:()=>normal};
 assert.strictEqual(bounds(item),normal);
 item.mcTooltipDummy={stage:{},getBounds:()=>({width:0,height:0})};assert.strictEqual(bounds(item),normal);
});
test('World-specific lot subclasses use the same native anchor',()=>{
 const measured={width:100,height:80};const item={kind:'WorldSpecificLot',lotId:10,GetData:()=>({}),mcPositionHelper:{},mcMapTag:{},mcTooltipDummy:{stage:{},getBounds:()=>measured},getBounds:()=>({width:800,height:500})};
 assert.strictEqual(bounds(item),measured);
});
test('Unrelated controls never use a similarly named anchor',()=>{
 const normal={width:80,height:50};assert.strictEqual(bounds({kind:'Other',getBounds:()=>normal,mcTooltipDummy:{stage:{},getBounds:()=>({width:400,height:300})}}),normal);
});
function fixture(type='MoveInPanel'){
 const panel={kind:'widgets.GameEntry.MovePanel.controls::'+type};
 for(const name of ['ddInOptions','ddOutOptions','txtRemainingFunds','btnOkay','btnClose'])panel[name]={parent:panel,visible:true,stage:{},text:name};
 panel.ddOutOptions.visible=false;panel.ddInOptions.text='Unfurnished';panel.txtRemainingFunds.text='Remaining Funds: 22,302';
 const ui={A11yIsLive:o=>!!o&&o.visible&&o.stage,A11yCollectText:(o,result)=>result.push(o.text),A11yIsInside:(o,root)=>{while(o){if(o===root)return true;o=o.parent;}return false;}};
 return {panel,ui};
}
test('Purchase confirmation reads current choice and remaining funds for residential panels',()=>{
 for(const type of ['MoveInPanel','PlexLotMoveInPanel','MultiUnitMoveInPanel']){
  const f=fixture(type),result=[];quote.call(f.ui,f.panel.btnOkay,result);assert.deepStrictEqual(result,['Unfurnished','Remaining Funds: 22,302']);
 }
});
test('Returning to the selector reads changed funds, including negative funds',()=>{
 const f=fixture(),result=[];f.panel.ddInOptions.text='Furnished';f.panel.txtRemainingFunds.text='Remaining Funds: -500';quote.call(f.ui,f.panel.ddInOptions,result);assert.deepStrictEqual(result,['Furnished','Remaining Funds: -500']);
});
test('Visible moving-out furniture choice is also included',()=>{
 const f=fixture(),result=[];f.panel.ddOutOptions.visible=true;f.panel.ddOutOptions.text='Sell furniture';quote.call(f.ui,f.panel.btnOkay,result);assert.equal(result[0],'Sell furniture');
});
test('Cancel and detached dropdown rows do not repeat the quote',()=>{
 const f=fixture(),result=[];quote.call(f.ui,f.panel.btnClose,result);quote.call(f.ui,{kind:'DropdownRow'},result);assert.equal(result.length,0);
});
test('Blueprint and venue purchases are not treated as household move-in',()=>{
 const f=fixture('PurchaseVenuePanel'),result=[];quote.call(f.ui,f.panel.btnOkay,result);assert.equal(result.length,0);
});
assert(source.includes('this.A11yMoveInQuote(param1,_loc2_)'));
console.log(count+' move-in checks passed (source fixtures; live checks required).');
