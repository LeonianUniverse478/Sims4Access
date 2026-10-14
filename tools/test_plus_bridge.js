'use strict';
// TS4 Access Plus catalog bridge, merged into TooltipManager (2026-10-08):
// "A11y|plus|..." messages reach A11yPlusHandle; a catalog category is
// listed through BBRequestProductCatalog in pages of 25, and select calls
// the chosen CatalogProduct's Select as a catalog click does. Added code
// follows GFX-SAFETY (no ++ or --, try/catch at the entry point).
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name,ctx){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+(Class|Array|DisplayObject)\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*\w+/g,'')+'){'+strip(source.slice(start,at-1))+'})',ctx);
}
let checks=0;
const posts=[],listeners=[],selected=[];
let catalogRequest=null;
class ProductFilter{ToObject(){return {productType:this.productType,categoryTags:this.categoryTags};}}
class CatalogProduct{constructor(raw){this.Name=raw.n;this.price=raw.p;this.variationCount=raw.v;this.stateIndex=raw.s;}
 Select(a,b,c,d,state){selected.push([this.Name,a,b,c,d,state]);}}
const defs={'gamedata.BuildBuy.shared.ProductFilter':ProductFilter,'gamedata.BuildBuy.shared.CatalogProduct':CatalogProduct,
 'gamedata.BuildBuy.constants.FilterCategories':{BUILDTAG_DOOR:111,BUILDTAG_WINDOW:222},
 'olympus.utils.TuningTagsUtils':{GetTagValueFromHash:h=>h+1}};
let rows=[];
const ctx={getDefinitionByName:n=>defs[n],Error:Error,encodeURIComponent:encodeURIComponent,String:String,int:v=>v|0,Array:Array,
 CommunicationManager:{CallGameService:(name,arg)=>{catalogRequest=[name,arg];return rows;},
  AddMessageListenerByName:(m,fn,owner)=>listeners.push([m,owner])}};
const ui={mA11yPlusProducts:[],mA11yPlusListening:false,A11yPostToPython:(cmd,payload)=>posts.push([cmd,decodeURIComponent(payload)])};
for(const name of ['A11yPlusHandle','A11yPlusReply','A11yPlusCatalog','A11yPlusSelect'])ui[name]=method(name,ctx);
ctx.int=v=>parseInt(v,10)|0;
ui.A11yPlusHandle(['A11y','plus','ping']);
assert.deepStrictEqual(posts.pop(),['a11yplus.flash','pong']);assert.deepStrictEqual(listeners,[['BBNotifyError','A11yPlus']]);checks++;
rows=[];for(let i=0;i<30;i=i+1)rows.push({n:'Door '+i,p:100+i,v:2,s:i%3});
ui.A11yPlusHandle(['A11y','plus','catalog','2','BUILDTAG_DOOR,UNKNOWN','9']);
assert.deepStrictEqual(catalogRequest,['BBRequestProductCatalog',{productType:2,categoryTags:[112]}]);checks++;
assert.strictEqual(posts.length,3,'two pages and the end');
assert(posts[0][1].startsWith('cat|9|0|30|Door%200~100~2^'));assert(posts[1][1].startsWith('cat|9|25|30|Door%2025~125~2'));
assert.strictEqual(posts[2][1],'catend|9|30');checks++;
posts.length=0;ui.A11yPlusHandle(['A11y','plus','select','4']);
assert.deepStrictEqual(selected,[['Door 4',null,null,0,2,1]]);assert.strictEqual(posts.pop()[1],'selected|4|Door%204');checks++;
ui.A11yPlusHandle(['A11y','plus','select','99']);assert.strictEqual(posts.pop()[1],'error|no such product');checks++;
assert.strictEqual(listeners.length,1,'the error listener is added once');checks++;
assert(/if\(_loc2_\[1\] == "plus" && _loc2_\.length >= 3\) \{ this\.A11yPlusHandle\(_loc2_\); return; \}/.test(source),'dispatched from A11yHandleEncoded');checks++;
const added=source.slice(source.indexOf('public function A11yPlusHandle'),source.indexOf('public function A11yHandleEncoded'));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' Plus catalog bridge checks passed');
