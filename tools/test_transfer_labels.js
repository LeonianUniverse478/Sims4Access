'use strict';
// Household transfer and move labels: Household Split and Merge, the shared
// Transfer Funds panel and the retail Transfer Funds dialog name where Sims
// and money go (A11yTransferQuote); the move dialog's furnishing dropdowns
// name which home they are for (A11yMoveLabel). Direction follows EA's
// TransferFundsPanel: the left household is the source, btnTransferRight
// moves money left to right and btnTransferLeft right to left.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+DisplayObject\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(source.slice(start,at-1))+'})',
  {TextField:o=>o,Error:Error});
}
function node(fields,parent){const n=Object.assign({live:true},fields||{});n.parent=parent||null;
 for(const v of Object.values(fields||{}))if(v&&typeof v==='object'&&!Array.isArray(v)&&v!==n&&!v.parent)v.parent=n;return n;}
function ctx(){
 const c={A11yIsLive:o=>!!o&&o.live!==false,
  A11yIsInside:(item,root)=>{for(let n=item;n;n=n.parent)if(n===root)return true;return false;},
  A11yCollectText:(n,out)=>{if(n&&n.say)out.push('5|5|'+n.say);}};
 c.A11yJoinedText=method('A11yJoinedText');c.A11yTransferQuote=method('A11yTransferQuote');c.A11yMoveLabel=method('A11yMoveLabel');
 return c;
}
const D='\u0002';
function household(name){return node({txtHouseholdName:{text:name},slTransferSims:node({}),cbSellFurnishings:node({})});}
function transferPanel(){
 const funds=node({txtSourceFamily:{text:'Fields'},txtTargetFamily:{text:'Goth'},txtAmountLabel:{text:'Amount:'},
  mcLeftFunds:node({say:'§12,000'}),mcRightFunds:node({say:'§0'}),btnTransferLeft:node({}),btnTransferRight:node({}),txtAmount:node({})});
 const panel=node({btnTransferTo:node({}),btnTransferFrom:node({}),mcSourceHousehold:household('Fields'),
  mcTargetHousehold:household('Goth'),mcTransferFundsPanel:funds});
 return {panel,funds};
}
let checks=0;
function quote(item){const out=[];ctx().A11yTransferQuote(item,out);return out;}
{const {funds}=transferPanel();
 assert.deepStrictEqual(quote(funds.btnTransferRight),['0|0|'+D+'dir'+D+'funds'+D+'Fields'+D+'Goth',
  '99000|0|'+D+'dir'+D+'has'+D+'Fields'+D+'§12,000','99999|0|'+D+'dir'+D+'has'+D+'Goth'+D+'§0']);checks++;
 assert.strictEqual(quote(funds.btnTransferLeft)[0],'0|0|'+D+'dir'+D+'funds'+D+'Goth'+D+'Fields','left arrow: right to left');checks++;
 assert.strictEqual(quote(funds.txtAmount)[0],'0|0|Amount:','the amount field says its label');checks++;}
{const {panel}=transferPanel();
 assert.deepStrictEqual(quote(panel.btnTransferTo),['0|0|'+D+'dir'+D+'sims'+D+'Fields'+D+'Goth']);checks++;
 assert.deepStrictEqual(quote(panel.btnTransferFrom),['0|0|'+D+'dir'+D+'sims'+D+'Goth'+D+'Fields']);checks++;
 const kim=node({},panel.mcSourceHousehold.slTransferSims),mort=node({},panel.mcTargetHousehold.slTransferSims);
 assert.deepStrictEqual(quote(kim),['99999|0|'+D+'dir'+D+'in'+D+'Fields'+D]);
 assert.deepStrictEqual(quote(mort),['99999|0|'+D+'dir'+D+'in'+D+'Goth'+D]);checks++;
 assert.deepStrictEqual(quote(panel.btnTransferTo.parent.mcSourceHousehold),[],'other controls are left alone');checks++;}
{const retail=node({ddFrom:node({say:'Fields Shop §1,200'}),ddTo:node({say:'Fields §9,000'}),btnSwap:node({}),
  txtAmountInput:node({}),txtAmountTranslated:node({say:'§500'}),btnConfirm:node({})});
 assert.deepStrictEqual(quote(retail.ddFrom),['0|0|'+D+'dir'+D+'from'+D+D]);
 assert.deepStrictEqual(quote(retail.ddTo),['0|0|'+D+'dir'+D+'to'+D+D]);
 assert.deepStrictEqual(quote(retail.btnConfirm),['99999|0|'+D+'dir'+D+'retail'+D+'§500'+D+'Fields Shop §1,200'+D+'Fields §9,000']);checks++;}
{const move=node({ddOutOptions:node({}),ddInOptions:node({}),txtMoving:node({say:'Moving Out'}),txtInOptions:node({say:'New Home'})});
 const out=[],inn=[];ctx().A11yMoveLabel(move.ddOutOptions,out);ctx().A11yMoveLabel(move.ddInOptions,inn);
 assert.deepStrictEqual(out,['0|0|Moving Out']);assert.deepStrictEqual(inn,['0|0|New Home']);checks++;}
assert(/this\.A11yMoveInQuote\(param1,_loc2_\); this\.A11yTransferQuote\(param1,_loc2_\); this\.A11yMoveLabel\(param1,_loc2_\);/.test(source),'wired into widget and focus reads');checks++;
const added=source.slice(source.indexOf('public function A11yJoinedText'),source.indexOf("// Game Options rows keep their localized name"));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' transfer label checks passed');
