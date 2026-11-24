'use strict';
// Catalog tree bridge (2026-10-14): A11yCatalogTags resolves FilterCategories
// names as FilterButton.CategoryTags does (an Array is a group for
// TuningTagsUtils.GetGroup, a single hash goes through GetTagValueFromHash),
// and A11yCatalogBrowse requests BBRequestProductCatalog for one Buy panel
// button or for a search (BuildBuyNavigationMain.OnSearch: searchResult.devString
// sorted by SEARCHGROUP_OPENSEARCH_SORT), replying in A11yPlusCatalog's pages.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function body(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 return [sig[1],source.slice(start,at-1)];
}
function method(name,ctx){
 const [args,code]=body(name);
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+(Class|Array|DisplayObject|Object)\b/g,'').replace(/ is Array\b/g,' instanceof Array');
 return vm.runInNewContext('(function('+strip(args).replace(/\s*=\s*[^,]+/g,'')+'){'+strip(code)+'})',ctx);
}
let checks=0;
const requests=[],replies=[];
class ProductFilter{constructor(){this.productType=2;this.categoryTags=[];this.categoryPriorityTags=[];this.searchResult=null;}ToObject(){return {productType:this.productType,categoryTags:this.categoryTags.slice(),categoryPriorityTags:this.categoryPriorityTags.slice(),search:this.searchResult&&this.searchResult.devString};}}
class SearchResult{constructor(){this.devString='';}}
class CatalogProduct{constructor(raw){Object.assign(this,raw);}}
const FilterCategories={BUYCAT_PA_REFRIGERATOR:0x11,BUYCAT_PA_STOVE:0x12,BUYGROUP_STOVE:[0x12,0x13],SEARCHGROUP_OPENSEARCH_SORT:[0x99]};
const TuningTagsUtils={GetTagValueFromHash:h=>({0x11:1001,0x12:1002})[h],GetGroup:a=>a.map(h=>({0x12:1002,0x13:1003,0x99:1099})[h])};
let catalog=[];
const defs={'gamedata.BuildBuy.shared.ProductFilter':ProductFilter,'gamedata.BuildBuy.shared.SearchResult':SearchResult,
 'gamedata.BuildBuy.shared.CatalogProduct':CatalogProduct,'gamedata.BuildBuy.constants.FilterCategories':FilterCategories,
 'olympus.utils.TuningTagsUtils':TuningTagsUtils};
const ctx={getDefinitionByName:n=>{assert(n in defs,n);return defs[n];},encodeURIComponent,decodeURIComponent,String,int:v=>v|0,Array,
 CommunicationManager:{CallGameService:(n,a)=>{assert.strictEqual(n,'BBRequestProductCatalog');requests.push(a);return catalog;}}};
const tm={mA11yPlusProducts:[],A11yPlusReply:t=>replies.push(t)};
for(const n of ['A11yCatalogTags','A11yCatalogBrowse','A11yPlusSelect']){const f=method(n,ctx);tm[n]=(...a)=>f.apply(tm,a);}
assert.deepStrictEqual(Array.from(tm.A11yCatalogTags('BUYCAT_PA_REFRIGERATOR')),[1001]);
assert.deepStrictEqual(Array.from(tm.A11yCatalogTags('BUYGROUP_STOVE')),[1002,1003],'a group expands');
assert.deepStrictEqual(Array.from(tm.A11yCatalogTags('')),[]);
assert.deepStrictEqual(Array.from(tm.A11yCatalogTags('NOT_A_TAG,BUYCAT_PA_STOVE')),[1002],'unknown names are skipped');checks++;
catalog=Array.from({length:30},(_,i)=>({Name:'Fridge '+i,price:1000+i,variationCount:2}));
tm.A11yCatalogBrowse(2,'BUYGROUP_STOVE','BUYCAT_PA_STOVE','7','');
assert.deepStrictEqual(JSON.parse(JSON.stringify(requests[0])),{productType:2,categoryTags:[1002,1003],categoryPriorityTags:[1002],search:null});
assert.strictEqual(replies.length,3,'two pages and an end');
assert(replies[0].startsWith('cat|7|0|30|Fridge%200~1000~2~^'));assert(replies[1].startsWith('cat|7|25|30|'));assert.strictEqual(replies[2],'catend|7|30');checks++;
replies.length=0;catalog=[{Name:'Double Bed',price:900,variationCount:3,Description:'Sleep like a log.'}];
tm.A11yCatalogBrowse(2,'','','8','double bed');
assert.deepStrictEqual(JSON.parse(JSON.stringify(requests[1])),{productType:2,categoryTags:[],categoryPriorityTags:[1099],search:'double bed'},'open search, as the Buy panel does');
assert.deepStrictEqual(replies,['cat|8|0|1|Double%20Bed~900~3~Sleep%20like%20a%20log.','catend|8|1'],'the catalog description rides along (2026-11-22)');checks++;
let selected=null;tm.mA11yPlusProducts[0].Select=(a,b,c,d,e)=>{selected=[c,d,e];};tm.mA11yPlusProducts[0].stateIndex=0;
tm.A11yPlusSelect(0);assert.deepStrictEqual(selected,[0,2,0]);assert.strictEqual(replies.pop(),'selected|0|Double%20Bed');checks++;
replies.length=0;
const longText=i=>'Lamp '+i+' '+'y'.repeat(392)+'\u{1F600}'+'z'.repeat(2100)+' end '+i;
catalog=Array.from({length:12},(_,i)=>({Name:'Lamp '+i,price:50,variationCount:1,Description:i%2?longText(i):'Short '+i}));
tm.A11yCatalogBrowse(2,'BUYCAT_PA_STOVE','','10','');
assert(replies.every(r=>r.length<4000),'every message stays a short command line');
assert.strictEqual(replies[replies.length-1],'catend|10|12','the end comes after every piece');
const got={},names=[];let at=0;
for(const r of replies){const p=r.split('|');
 if(p[0]==='cat'){assert.strictEqual(+p[2],at);for(const it of p[4].split('^')){const b=it.split('~');names.push(decodeURIComponent(b[0]));if(b[3])got[at]=decodeURIComponent(b[3]);at++;}}
 if(p[0]==='catdesc'){assert(+p[2]<at,'a piece follows its item');got[+p[2]]=(got[+p[2]]||'')+decodeURIComponent(p[3]);}}
assert.strictEqual(names.length,12,'every item arrives once');
for(let i=0;i<12;i++)assert.strictEqual(got[i],i%2?longText(i):'Short '+i,'description '+i+' arrives whole, never cut (2026-11-23)');checks++;
replies.length=0;catalog=null;tm.A11yCatalogBrowse(2,'BUYCAT_PA_STOVE','','9','');assert.deepStrictEqual(replies,['catend|9|0'],'no answer is an empty list');checks++;
assert(/cmd == "browse" && parts\.length >= 8\) \{ this\.A11yCatalogBrowse\(int\(parts\[3\]\),String\(parts\[4\]\),String\(parts\[5\]\),String\(parts\[6\]\),decodeURIComponent\(String\(parts\[7\]\)\)\); \}/.test(source),'browse is dispatched');
const added=source.slice(source.indexOf('public function A11yCatalogTags'),source.indexOf('public function A11yHandleEncoded'));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' catalog bridge checks passed');
