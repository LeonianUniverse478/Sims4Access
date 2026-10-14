'use strict';
// Escape in the Build catalog leaves it: A11yDismiss -> A11yReleaseBuildCatalog
// releases keyboard ownership (modalstate 00, so the lot grid chords reach the
// world) without any EA call, keeps the release across frames and across a
// dialog shown above it, and Tab returns to the catalog. Other owners keep
// their Escape. Runs the real A11yModalFrame, A11yIsModalScope and handlers.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
class DisplayObjectContainer { constructor(name){this.name=name;this.kids=[];} contains(o){return o===this||this.kids.includes(o);} }
class TextField {}
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObjectContainer|DisplayObject|TextField|Event|String|Object|Boolean|Number|Array|Error|int)\b/g,'').replace(/\s+as\s+DisplayObject\b/g,'').replace(/\bis\s+(DisplayObjectContainer|TextField)\b/g,'instanceof $1');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(source.slice(start,at-1))+'})',
  {getQualifiedClassName:o=>o&&o.kind||'Widget',DisplayObjectContainer,TextField,getTimer:()=>1000,
   CommunicationManager:{CallUIService:()=>{calls.push('ui');return true;},CallGameService:()=>{calls.push('game');}}});
}
let calls=[],checks=0;
function fixture(){
 const catalog=new DisplayObjectContainer('catalog');catalog.kind='BuildBuyProductCatalogMain';catalog.WidgetName='BuildBuyProductCatalog';
 const cell=new DisplayObjectContainer('cell');catalog.kids.push(cell);
 const dialog=new DisplayObjectContainer('dialog');
 const picker=new DisplayObjectContainer('picker');picker.kind='PickersMain';
 const posts=[],focused=[];
 const w={top:catalog,dialog:null,hudMode:2};
 const ctx={A11yGuideFrame:()=>{}, // the guided New Game has its own suite (test_guided_new_game.js)
  mA11yKeyboard:true,mA11yHudMode:2,mA11yHudBrowsing:false,mA11yScopeHistory:[],mA11yScope:null,mA11yPendingScope:null,
  mA11yActiveModalRoot:null,mA11yStatusScope:null,mA11yFocused:null,mA11yDropdown:null,mA11yBuildCursor:false,mA11yBuildMarker:null,
  mA11yCatalogReleased:null,mA11yOwnerReported:'',mA11yModalReported:'',mA11yBlockingReported:'',mA11yScannerOwnerReported:'',
  mA11yScannerLiveReported:'',mA11yScannerMode:false,mA11yStartupActive:false,mA11yManagedDialog:null,
  mA11yDialogManager:{IsInstantiated:()=>true,GetCurrentRequest:()=>w.dialog?{dialog:w.dialog}:null},
  mTooltipsLayer:{stage:{focus:null}},
  A11yWorldHudMode:()=>w.hudMode,A11yTopModalWidget:()=>w.top,A11yOpenHud:()=>null,
  A11yLoadedWidget:n=>n==='BuildBuyProductCatalog'?catalog:null,
  A11yIsLive:o=>!!o&&!o.dead,A11yIsAbove:()=>true,A11yIsInside:(a,b)=>!!a&&!!b&&b.contains&&b.contains(a),
  A11ySeasonScope:()=>null,A11yCASStoryScope:()=>null,A11yFilterPopup:()=>null,A11yCurrentDropdown:()=>null,
  A11yFindDropdownExtension:()=>null,A11yBuildBlocked:()=>false,
  A11yFocusHover:()=>{},A11yFocusInto:o=>{focused.push(o.name);ctx.mA11yScope=o;ctx.mA11yFocused=o===catalog?cell:o;},
  A11yClearFocus:()=>{ctx.mA11yFocused=null;},A11yCancelIndex:()=>{},A11yClearRing:()=>{},A11yFocusSettled:()=>{},
  A11yDrawFocusRing:()=>{},A11yBuildFrame:()=>{},A11yPhoneFrame:()=>{},A11yFollowCASInput:()=>{},
  A11yScannerOwner:()=>false,A11yFirstPersonState:()=>false,A11yClickControl:()=>true,
  A11yTabControl:d=>{calls.push('tab'+d);},A11yNativeTab:d=>d,
  A11yPostToPython:(c,p)=>posts.push([c,decodeURIComponent(p)])};
 for(const n of ['A11yModalFrame','A11yIsModalScope','A11yPhoneBlocking','A11yDismiss','A11yReleaseBuildCatalog','A11yIsBuildBuy','A11yBuildCatalogOwner','A11yReturnToCatalog','A11yMsgTabNext','A11yMsgTabPrev'])ctx[n]=method(n);
 const state=()=>posts.filter(p=>p[0]==='a11y.modalstate').map(p=>p[1]).pop();
 return {ctx,w,catalog,cell,dialog,picker,posts,focused,state};
}
{
 const f=fixture();calls=[];
 f.ctx.A11yModalFrame();
 assert.strictEqual(f.state(),'10');assert.deepStrictEqual(f.focused,['catalog']);checks++;           // the catalog owns the keys
 f.ctx.A11yDismiss();                                                                               // Escape
 assert(f.posts.some(p=>p[0]==='a11y.catalogleft'),'announced');assert.deepStrictEqual(calls,[],'no EA call');
 assert.strictEqual(f.ctx.mA11yScope,null);assert.strictEqual(f.ctx.mA11yFocused,null);checks++;
 f.ctx.A11yModalFrame();f.ctx.A11yModalFrame();
 assert.strictEqual(f.state(),'00','released: grid chords reach the world');assert.deepStrictEqual(f.focused,['catalog']);checks++;
 f.w.dialog=f.dialog;f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'10');                   // a dialog above it owns the keys
 f.w.dialog=null;f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'00','still released after the dialog');checks++;
 f.ctx.A11yMsgTabNext();assert.deepStrictEqual(calls,[],'Tab returns instead of tabbing the HUD');
 f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'10');assert.deepStrictEqual(f.focused,['catalog','dialog','catalog']);checks++;
 f.ctx.A11yMsgTabNext();assert.deepStrictEqual(calls,['tab1'],'ordinary Tab afterwards');checks++;
 f.ctx.A11yDismiss();f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'00');
 f.w.hudMode=1;f.ctx.A11yModalFrame();assert.strictEqual(f.ctx.mA11yCatalogReleased,null,'leaving Build forgets the release');checks++;
}
{
 const f=fixture();calls=[];f.ctx.A11yModalFrame();f.ctx.A11yDismiss();
 f.catalog.dead=true;f.w.top=null;f.ctx.A11yModalFrame();
 assert.strictEqual(f.ctx.mA11yCatalogReleased,null,'a closed catalog clears the release');checks++;
}
{
 const f=fixture();f.w.top=f.picker;f.ctx.A11yModalFrame();calls=[];
 f.ctx.A11yDismiss();
 assert(!f.posts.some(p=>p[0]==='a11y.catalogleft'),'other owners keep their Escape');
 assert.strictEqual(f.ctx.mA11yCatalogReleased,null);checks++;
}
{
 // EA registers the catalog under a name we do not list: recognised by its Build/Buy class.
 const f=fixture();const other=new DisplayObjectContainer('panel');other.kind='widgets.BuildBuy::BuildBuyCatalogPanelMain';
 f.w.top=other;f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'10');
 f.ctx.A11yDismiss();assert(f.posts.some(p=>p[0]==='a11y.catalogleft'));
 f.ctx.A11yModalFrame();f.ctx.A11yModalFrame();assert.strictEqual(f.state(),'00','an unlisted Build/Buy widget stays released');checks++;
}
{
 // Reached by Tab (HUD browsing), focus inside the catalog: Escape releases it too.
 const f=fixture();f.w.top=null;f.cell.parent=f.catalog;
 f.ctx.mA11yHudBrowsing=true;f.ctx.mA11yScope=f.ctx.mTooltipsLayer.stage;f.ctx.mA11yFocused=f.cell;
 f.ctx.A11yDismiss();
 assert(f.posts.some(p=>p[0]==='a11y.catalogleft'),'HUD-browsed catalog released');
 assert.strictEqual(f.ctx.mA11yHudBrowsing,false);assert.strictEqual(f.ctx.mA11yScope,null);
 assert.strictEqual(f.ctx.mA11yCatalogReleased,f.catalog);
 // It was not modal: Tab browses the Build panels again instead of only clearing.
 calls=[];f.ctx.A11yMsgTabNext();assert.deepStrictEqual(calls,['tab1']);checks++;
}
{
 // HUD browsing on something that is not Build/Buy keeps the ordinary HUD Escape.
 const f=fixture();f.w.top=null;const button=new DisplayObjectContainer('button');button.parent=null;
 f.ctx.mA11yHudBrowsing=true;f.ctx.mA11yScope=f.ctx.mTooltipsLayer.stage;f.ctx.mA11yFocused=button;
 f.ctx.A11yDismiss();assert(!f.posts.some(p=>p[0]==='a11y.catalogleft'));
 assert.strictEqual(f.ctx.mA11yHudBrowsing,false,'ordinary HUD exit');assert.strictEqual(f.ctx.mA11yCatalogReleased,null);checks++;
}
{
 // Live mode never treats anything as the Build catalog.
 const f=fixture();f.w.hudMode=1;f.ctx.mA11yHudMode=1;f.ctx.A11yModalFrame();f.ctx.A11yDismiss();
 assert(!f.posts.some(p=>p[0]==='a11y.catalogleft'));checks++;
}
const added=source.slice(source.indexOf('public function A11yReleaseBuildCatalog'),source.indexOf('public function A11yBuildReply'));
assert(!/\+\+|--/.test(added),'no increment operators');checks++;
console.log(checks+' Build catalog Escape checks passed');
