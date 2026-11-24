'use strict';
// Execute the actual footer transition; do not click or purchase in a game.
const fs=require('fs'), path=require('path'), vm=require('vm'), assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
const strip=s=>s.replace(/(\w):\s*(DisplayObject|Object|String|Boolean|Error|Rectangle|Stage|int)\b/g,'$1')
 .replace(/\s+as\s+(DisplayObject|Stage)\b/g,'').replace(/ is TextField\b/g,' instanceof TextField')
 .replace(/(_loc4_\["(?:IncreaseAmount|DecreaseAmount)"\]) is Function/g,'typeof $1 === "function"');
let keyCalls=0;
const context={encodeURIComponent,getDefinitionByName:name=>{keyCalls++;assert.equal(name,'olympus.localization.KeysConsole');return {PURCHASE_PICKER_EMPTY_CART:{toString:()=> 'Your cart is empty.'}};}};
function method(text,name){
 const header=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(text);assert(header,name);
 let at=header.index+header[0].length,start=at,depth=1;
 while(depth){if(text[at]==='{')depth++;if(text[at]==='}')depth--;at++;}
 return vm.runInNewContext('(function('+strip(header[1])+'){'+strip(text.slice(start,at-1))+'})',context);
}
const fn=method(source,'A11yPickerFooter');
function fixture(enabled,reason=''){
 const stage={},button={enabled,live:true,TooltipExt:{Text:reason}};
 const owner={btnDone:button,parent:stage},row={parent:owner};
 const ui={mTooltipsLayer:{stage},mA11yFocused:row,focused:[],activated:[],posts:[],
  A11yIsLive:b=>b.live,A11yFocusItem(b){this.focused.push(b);this.mA11yFocused=b;},
  A11yActivate(confirm){this.activated.push(confirm);},A11yPostToPython(...args){this.posts.push(args);}};
 return {stage,button,owner,row,ui};
}
let checks=0;
{const f=fixture(false);assert.equal(fn.call(f.ui,f.row),true);assert.equal(f.ui.mA11yFocused,f.row);
 assert.equal(f.ui.focused.length,0);assert.equal(f.ui.activated.length,0);
 const spoken=decodeURIComponent(f.ui.posts[0][1]);assert(spoken.includes('Your cart is empty.'));assert(spoken.includes('Right and Left'));
 assert.deepStrictEqual(f.ui.posts[1],['a11y.mark','purchase-footer-disabled']);checks++;}
{const before=keyCalls,f=fixture(false,'Not enough funds.');fn.call(f.ui,f.row);
 assert(decodeURIComponent(f.ui.posts[0][1]).includes('Not enough funds.'));assert.equal(keyCalls,before);assert.equal(f.ui.mA11yFocused,f.row);checks++;}
{const f=fixture(true);assert.equal(fn.call(f.ui,f.row),true);assert.deepStrictEqual(f.ui.focused,[f.button]);assert.equal(f.ui.activated.length,0);assert.equal(f.ui.posts.length,0);checks++;}
{const f=fixture(false);f.button.live=false;assert.equal(fn.call(f.ui,f.row),false);assert.equal(f.ui.posts.length,0);assert.equal(f.ui.focused.length,0);checks++;}
{const f=fixture(true);f.owner.mcNextButton=f.button;assert.equal(fn.call(f.ui,f.row,true),true);assert.deepStrictEqual(f.ui.activated,[false]);checks++;}
{const f=fixture(false);f.owner.mcNextButton=f.button;assert.equal(fn.call(f.ui,f.row,true),true);assert.equal(f.ui.activated.length,0);assert.equal(f.ui.posts.length,0);checks++;}
{const f=fixture(false);context.getDefinitionByName=()=>{throw Error('unavailable');};assert.doesNotThrow(()=>fn.call(f.ui,f.row));assert(decodeURIComponent(f.ui.posts[0][1]).includes('Choose an item quantity'));checks++;}
function cart(increaseAllowed){
 const f=fixture(false);let quantity=0,buys=0;
 context.getDefinitionByName=()=>({PURCHASE_PICKER_EMPTY_CART:{toString:()=> 'Your cart is empty.'}});
 context.TextField=function(){};context.getQualifiedClassName=o=>o.kind||'Button';
 context.MouseEvent={MOUSE_DOWN:'down',MOUSE_UP:'up',CLICK:'click'};
 context.Event=function(type){this.type=type;};context.PurchasePicker={INCREASE_AMOUNT_EVENT:'increase'};
 const cellSource=fs.readFileSync(path.join(__dirname,'../flash/extra-classes/PurchasePickerCellView.as'),'utf8');
 const increase=method(cellSource,'IncreaseAmount');
 Object.assign(f.row,{kind:'widgets.Pickers.controls.PurchasePicker::PurchasePickerCellView',stage:f.stage,live:true,
  btnIncrease:{enabled:increaseAllowed},mNumAvailable:-1,A11yQueueAmountAnnounce(){},
  dispatchEvent(event){assert.equal(event.type,'increase');quantity++;f.button.enabled=quantity*150<=154483;},
  IncreaseAmount(){increase.call(this);},DecreaseAmount(){throw Error('Unexpected decrease');}});
 f.button.stage=f.stage;
 Object.assign(f.ui,{mA11yScope:{stage:f.stage},mA11yKeyboard:true,mA11yIdxDir:0,mA11yPendingScope:null,
  mA11yNavQueue:[],mA11ySimplifiedMenus:false,A11yModalFrame(){},A11yIsModalScope:()=>true,
  A11yCalendarStep:()=>false,A11ySeasonActivate:()=>false,A11yPlexActivate:()=>false,A11yActivateCASName:()=>false,
  A11yActionProxy:x=>x,A11yInformational:()=>false,A11yInventoryMenu:()=>false,A11yPickerToggleCell:()=>false,
  A11yGridStep(){throw Error('Quantity row must not move focus');},
  A11ySafeDispatch(target,type){assert.equal(target,f.button);if(type==='click'){assert(f.button.enabled);buys++;}}});
 for(const name of ['A11yFindStepper','A11yArrowHorizontal','A11yActivate','A11yPickerFooter'])f.ui[name]=method(source,name);
 return Object.assign(f,{quantity:()=>quantity,buys:()=>buys});
}
{const f=cart(true);f.ui.A11yActivate();assert.equal(f.ui.mA11yFocused,f.row);assert.equal(f.quantity(),0);assert.equal(f.buys(),0);
 f.ui.A11yArrowHorizontal(1);assert.equal(f.quantity(),1);assert.equal(f.ui.mA11yFocused,f.row);
 f.ui.A11yActivate();assert.equal(f.ui.mA11yFocused,f.button);assert.equal(f.buys(),0);
 f.ui.A11yActivate();assert.equal(f.buys(),1);checks++;}
{const f=cart(false);f.ui.A11yArrowHorizontal(1);assert.equal(f.quantity(),0);
 f.ui.A11yActivate();assert.equal(f.ui.mA11yFocused,f.row);assert.equal(f.buys(),0);checks++;}
console.log(checks+' purchase footer checks passed (game validation retained).');
