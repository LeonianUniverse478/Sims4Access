'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
const start=source.indexOf('      public function A11yAnnounceScope(');
const end=source.indexOf('      public function A11yRentalQuote(',start);
const method=source.slice(start,end).replace('public function','function').replace(/:\s*(Array|String|void|Error)\b(?!\s*\()/g,'');
const run=vm.runInNewContext('('+method+')',{getQualifiedClassName:x=>x.kind,Array,String,Object,encodeURIComponent});
let introCalls=0,readCalls=0,messages=[];
const scope={kind:'widgets.GameEntry.RentalPanel::GERentalPanelMain'};
const ui={mA11yScope:scope,mA11yDropdown:null,mA11yHudRoot:null,mA11yManagedDialog:null,mA11yFocused:{},
 A11yIntroText:(root,parts)=>{assert.equal(root,scope);introCalls++;parts.push('0|0|Rent this lot','1|0|Funds 12409','2|0|397 per day');},
 A11yCollectText:(item,parts)=>parts.push('3|0|1'),A11yReadCurrent:()=>readCalls++,
 A11yPostToPython:(command,payload)=>messages.push([command,decodeURIComponent(payload)])};
run.call(ui);assert.equal(introCalls,1);assert.equal(readCalls,0);assert.equal(messages[0][0],'a11y.scope_enc');assert(messages[0][1].includes('dialog\u0002'));assert(messages[0][1].includes('397 per day'));
ui.mA11yDropdown=scope;run.call(ui);assert.equal(readCalls,1);assert.equal(introCalls,1);
ui.mA11yDropdown=null;scope.kind='widgets.Other::Panel';run.call(ui);assert.equal(readCalls,2);assert.equal(introCalls,1);
console.log('3 rental context checks passed');

const quoteStart=source.indexOf('      public function A11yRentalQuote(');
const quoteEnd=source.indexOf('      public function A11yFundsTarget(',quoteStart);
const quoteMethod=source.slice(quoteStart,quoteEnd).replace('public function','function')
 .replace(/:\s*(DisplayObject|Array|Object|String|int|void|Error)\b(?!\s*\()/g,'')
 .replace(/\s+as\s+DisplayObject\b/g,'').replace('for each(field in','for(field of');
const quote=vm.runInNewContext('('+quoteMethod+')',{getQualifiedClassName:x=>x.kind});
// EA's exported movie symbol is the subclass GERentalPanel, not its base class.
const panel={kind:'GERentalPanel',parent:null};
for(const name of ['txtRentFor','ddRentalTime','txtDays','txtCostCalculator','txtCost','btnOkayCreate','btnOkayExtend','btnClose']) {
 panel[name]={parent:panel,visible:true,text:name};
}
panel.ddRentalTime.text='2'; panel.txtCost.text='794';
const reader={A11yIsInside:(item,root)=>{while(item){if(item===root)return true;item=item.parent;}return false;},
 A11yCollectText:(item,parts)=>parts.push(item.text)};
let parts=[];quote.call(reader,panel.ddRentalTime,parts);assert(parts.includes('794'));assert(parts.includes('2'));
panel.txtCost.text='1191';parts=[];quote.call(reader,panel.btnOkayCreate,parts);assert(parts.includes('1191'));assert(!parts.includes('794'));
parts=[];quote.call(reader,panel.btnClose,parts);assert.equal(parts.length,0);
parts=[];quote.call(reader,{parent:null,kind:'DropdownRow',text:'3'},parts);assert.equal(parts.length,0);
panel.txtCost.visible=false;parts=[];quote.call(reader,panel.btnOkayExtend,parts);assert(!parts.includes('1191'));
parts=[];quote.call(reader,{parent:null,kind:'OtherPanel'},parts);assert.equal(parts.length,0);
assert(source.includes('this.A11yRentalQuote(param1,_loc2_)'));
console.log('6 current rental quote checks passed');
