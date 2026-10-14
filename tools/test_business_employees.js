'use strict';
// Business employee management (retail stores, WickedWhims strip club):
// each employee group is a container (A11yCompositeRow), so the Sims to hire
// are separate stops; a current employee's cell and its Promote, Demote and
// Fire buttons are collected even though EA disables the cell.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name,ctx){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+DisplayObject\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(source.slice(start,at-1))+'})',ctx);
}
let checks=0;
const ctx={getQualifiedClassName:o=>o.cls||'Object',Object:Object};
const composite=method('A11yCompositeRow',ctx);
const ui={mA11ySimplifiedMenus:false,A11ySimplifiedActive:()=>false};
assert.strictEqual(composite.call(ui,{cls:'widgets.Gameplay.BusinessEmployeeManagement.controls::EmployeeGroupCellView'}),true,'group is a container');checks++;
assert.strictEqual(composite.call(ui,{cls:'widgets.Gameplay.BusinessEmployeeManagement.controls::EmployeeCellView'}),false,'a Sim cell is a stop');checks++;
const collect=source.slice(source.indexOf('public function A11yCollectFocusables'),source.indexOf('public function A11yCollectFocusables')+12000);
const block=/if\("btnFire" in param1 && "btnPromote" in param1 && "btnDemote" in param1 && "mcSatisfactionTooltipHolder" in param1\)\r?\n\s*\{([\s\S]*?)return;\r?\n\s*\}/.exec(collect);
assert(block,'employee cell branch');checks++;
assert(/param2\.push\(param1\)/.test(block[1])&&/A11yInListViewport\(param1\)/.test(block[1]),'the cell is pushed with the usual viewport checks');checks++;
for(const name of ['btnPromote','btnDemote','btnFire'])assert(block[1].includes('Object(param1)["'+name+'"]'),name);checks++;
assert(collect.indexOf(block[0])<collect.indexOf('if(!this.A11yCompositeRow(param1) && (this.A11yIsFocusable(param1)'),'runs before the focusable test that skips disabled cells');checks++;
assert(!/\+\+|--/.test(block[0]),'no increment operators');checks++;
console.log(checks+' business employee checks passed');
