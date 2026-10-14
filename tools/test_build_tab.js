'use strict';
// Build mode Tab: A11yBuildSections/A11yCollectBuildSections order the
// Build panels as filters, search, Build/Buy/Function tabs, categories,
// products, swatches, and leave out EA's tool buttons (BuildBuyInspector).
// Only while browsing from the world in Build mode; otherwise the full-screen
// order is kept (the caller falls back when nothing is collected).
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+DisplayObject\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(source.slice(start,at-1))+'})',{});
}
function part(name,items){return {name,items,live:true};}
function fixture(over){
 const w=Object.assign({hud:2,browsing:true,modal:null,filter:true},over||{});
 const products=part('products',['bed','chair']);
 const panels={
  BuildBuyFilter:w.filter?part('filter',['price','style']):null,
  BuildBuyNavigation:{mcSearchContainer:part('search',['searchbox']),mcButtonContainer:part('tabs',['build','buy','function']),
                      mcNavPanel:part('categories',['bedroom','kitchen'])},
  BuildBuyProductCatalog:{mcCatalog:{mcCatalog:products,mcVariationSelector:part('swatches',['blue'])}},
  BuildBuyInspector:part('tools',['undo','sledgehammer'])};
 const ctx={mA11yHudBrowsing:w.browsing,mA11yActiveModalRoot:w.modal,
  A11yWorldHudMode:()=>w.hud,A11yIsLive:o=>!!o&&o.live!==false,A11yLoadedWidget:n=>panels[n]||null,
  A11yCollectFocusables:(root,out)=>{for(const item of root.items||[])out.push(item);},A11ySortFocusables:()=>0};
 ctx.A11yBuildSections=method('A11yBuildSections');ctx.A11yCollectBuildSections=method('A11yCollectBuildSections');
 return ctx;
}
let checks=0;
{const ctx=fixture();const all=[];assert.strictEqual(ctx.A11yCollectBuildSections(all),true);
 assert.deepStrictEqual(all,['price','style','searchbox','build','buy','function','bedroom','kitchen','bed','chair','blue']);
 assert(!all.includes('undo')&&!all.includes('sledgehammer'),'EA tool buttons are left out');checks++;}
{const ctx=fixture({filter:false});const all=[];ctx.A11yCollectBuildSections(all);
 assert.strictEqual(all[0],'searchbox','no open filter panel: search comes first');checks++;}
for(const [label,over] of [['Live mode',{hud:1}],['not browsing',{browsing:false}],['a dialog',{modal:{live:true}}]]){
 const ctx=fixture(over);const all=[];
 assert.strictEqual(ctx.A11yCollectBuildSections(all),false,label);assert.deepStrictEqual(all,[],label);checks++;
}
assert(/if\(!this\.A11yCollectBuildSections\(all\)\)\r?\n\s*\{\r?\n\s*this\.A11yCollectFocusables\(this\.mA11yScope != null/.test(source),'Tab falls back to the full order');checks++;
const added=source.slice(source.indexOf('public function A11yBuildSections'),source.indexOf('public function A11yMsgTabNext'));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' Build mode Tab checks passed');
