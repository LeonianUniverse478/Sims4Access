'use strict';
// Execute production AS3 methods; native movie/live checks are still required.
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');
function TextField() {}
const cameraState={active:false};
const clock={now:1000};
function method(name, input=source) {
  const header = new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(input);
  assert(header, name);
  let start=header.index+header[0].length, end=start, depth=1;
  while(depth) { if(input[end]==='{') depth++; if(input[end]==='}') depth--; end++; }
  const types=/:\s*(?:DisplayObjectContainer|DisplayObject|TextField|Stage|Boolean|Number|String|Object|Array|int|Error)\b/g;
  let body=input.slice(start,end-1).replace(types,'')
    .replace(/\s+as\s+DisplayObject\b/g,'').replace(/\bis\s+TextField\b/g,'instanceof TextField')
    .replace(/for each\((\w+) in ([^\n]+)\)/g,'for($1 of $2)');
  return vm.runInNewContext('(function('+header[1].replace(types,'')+'){'+body+'})',
    {TextField, int:Math.trunc, getQualifiedClassName:item=>item.kind || 'fixture',encodeURIComponent,getTimer:()=>clock.now,
     UiDialogMessage:{TYPE_OBJECT_MULTI_PICKER:9,TYPE_CUSTOMIZE_OBJECT_MULTI_PICKER:10},
     CommunicationManager:{CallGameService(name){assert.equal(name,'IsUsingCameraControllerFPS');return cameraState.active;}}});
}
let checks=0;
function test(name, fn) { fn(); checks++; console.log('PASS '+name); }
const tab=method('A11yTabControl'), arrow=method('A11yArrowNav');
const active=method('A11ySimplifiedActive');
const buildSections=method('A11yBuildSections'), collectBuildSections=method('A11yCollectBuildSections');
function fixture(simple=true) {
  const calls=[];
  const ctx={mA11yKeyboard:true,mA11ySimplifiedMenus:simple,mA11yScope:{stage:{}},
    mA11yTooltipsLayer:null,mTooltipsLayer:{stage:{focus:null}},mA11yNavQueue:[],
    mA11yPendingScope:null,mA11yIdxDir:0,
    A11ySimplifiedActive(){return active.call(this);},A11yGameState:()=>270579719,A11yCASStoryScope:()=>null,
    A11yModalFrame(){}, A11yIsModalScope(){return true;},
    A11yTabMove(d){calls.push(['option',d]);},
    A11yFindScrollList(){return null;}, A11yGroupOwner(){return null;},
    A11yCollectFocusables(_scope,all){calls.push(['groups']);},
    // The real Build mode section collector; a menu is not Build mode, so it
    // declines and Tab keeps its grouped order (2026-09-30).
    A11yWorldHudMode:()=>1, A11yBuildSections:buildSections, A11yCollectBuildSections:collectBuildSections,
    A11yCalendarStep(d){calls.push(['spatial',d]);return true;}};
  return {ctx,calls};
}
test('default is enabled in every new movie',()=>assert(source.includes('mA11ySimplifiedMenus:Boolean = true')));
for(const direction of [-1,1]) {
  test('Tab advances exactly one option '+direction,()=>{
    const {ctx,calls}=fixture();tab.call(ctx,direction);assert.deepStrictEqual(calls,[['option',direction]]);
  });
  test('Up/Down ignores spatial grid columns '+direction,()=>{
    const {ctx,calls}=fixture();arrow.call(ctx,direction);assert.deepStrictEqual(calls,[['option',direction]]);
  });
}
test('off restores grouped Tab navigation',()=>{
  const {ctx,calls}=fixture(false);tab.call(ctx,1);assert.deepStrictEqual(calls,[['groups']]);
});
test('off restores spatial arrow navigation',()=>{
  const {ctx,calls}=fixture(false);arrow.call(ctx,-1);assert.deepStrictEqual(calls,[['spatial',-1]]);
});
test('text editing keeps its arrows',()=>{
  const {ctx,calls}=fixture();ctx.mTooltipsLayer.stage.focus=new TextField();arrow.call(ctx,1);assert.deepStrictEqual(calls,[]);
});
test('pending transition queues one move without touching the next screen',()=>{
  const {ctx,calls}=fixture();ctx.mA11yPendingScope={};arrow.call(ctx,1);
  assert.deepStrictEqual(calls,[]);assert.deepStrictEqual(ctx.mA11yNavQueue,[5]);
});
test('world arrows are not mistaken for menu options',()=>{
  const {ctx,calls}=fixture();ctx.A11yIsModalScope=()=>false;arrow.call(ctx,1);assert.deepStrictEqual(calls,[]);
});
const position=method('A11yOptionPosition');
test('CAS and Stories retain existing navigation even when simplified is enabled',()=>{
  for(const mode of ['state','story','scope']) {
    const {ctx,calls}=fixture();
    if(mode==='state') ctx.A11yGameState=()=>983016380;
    if(mode==='story') ctx.A11yCASStoryScope=()=>({});
    if(mode==='scope') ctx.mA11yScope.kind='widgets.CAS.Stories::CASStoriesDialog';
    arrow.call(ctx,1);assert.deepStrictEqual(calls,[['spatial',1]],mode);
  }
});
test('position uses full virtualized list count rather than visible rows',()=>{
  const item={},layout={GetNumItems:()=>50};
  const ctx={mA11ySimplifiedMenus:true,mA11yFocused:item,A11yFindScrollList:()=>({}),
    A11ySimplifiedActive(){return this.mA11ySimplifiedMenus;},
    A11yGridLayout:()=>layout,A11yCellIndexOf:()=>29};
  assert.equal(position.call(ctx,item),'30 of 50');
  ctx.mA11ySimplifiedMenus=false;assert.equal(position.call(ctx,item),'');
});
test('ordinary options use their sequence; unrelated hover gets no position',()=>{
  const items=[{},{},{}],item=items[1];
  const ctx={mA11ySimplifiedMenus:true,mA11yFocused:item,mA11yScope:{},
    A11ySimplifiedActive:()=>true,
    A11yFindScrollList:()=>null,A11yCollectFocusables(_s,out){out.push(...items);},A11ySortFocusables:()=>0};
  assert.equal(position.call(ctx,item),'2 of 3');assert.equal(position.call(ctx,items[0]),'');
});
const set=method('A11ySetSimplifiedMenus');
test('setting transition fences queued input; repeated heartbeat does not',()=>{
  const calls=[],ctx={mA11ySimplifiedMenus:true,mA11yNavQueue:[1,1],mA11yList:[{}],
    A11yCancelIndex(){calls.push('cancel');},A11yFenceOpeningInput(){calls.push('fence');}};
  set.call(ctx,false);assert.deepStrictEqual(calls,['cancel','fence']);assert.equal(ctx.mA11yNavQueue.length,0);
  assert.equal(ctx.mA11yList,null);set.call(ctx,false);assert.equal(calls.length,2);
});
test('startup discovers both keyboard preferences and speech-only without inbound messages',()=>{
  const next=method('A11yNextStartupPort');
  assert.equal(next(45993),45995);assert.equal(next(45995),45994);assert.equal(next(45994),45993);
});
const guard=method('A11yGuardForBinding');
test('Live world Shift+Tab reaches the native first-person binding',()=>{
  const ctx={mA11yStartupActive:false,mA11yHudBrowsing:false,A11yWorldHudMode:()=>1,
    A11yModalFrame(){},A11yEditing:()=>false,A11yIsLive:()=>false,A11yIsModalScope:()=>false,A11yGuardValid:()=>true};
  assert.equal(guard.call(ctx,9,1),false);assert.equal(guard.call(ctx,9,0),true);
  ctx.mA11yHudBrowsing=true;assert.equal(guard.call(ctx,9,1),true);
  ctx.mA11yHudBrowsing=false;ctx.A11yIsModalScope=()=>true;assert.equal(guard.call(ctx,9,1),true);
  ctx.mA11yStartupActive=true;assert.equal(guard.call(ctx,9,1),true);
});
test('first-person announcements follow actual camera changes, not requested state',()=>{
  const current=method('A11yFirstPersonState'),said=[];
  const ctx={mA11yStartupActive:false,mA11yFirstPersonKnown:false,A11yWorldHudMode:()=>1,
    A11yPostToPython(channel,text){said.push([channel,decodeURIComponent(text)]);}};
  cameraState.active=false;assert.equal(current.call(ctx),false);assert.equal(said.length,0);
  cameraState.active=true;assert.equal(current.call(ctx),true);assert.equal(said.length,1);
  assert.equal(ctx.mA11yFirstPersonFence,1350);
  current.call(ctx);assert.equal(said.length,1);assert(said[0][1].includes('camera on'));
  cameraState.active=false;assert.equal(current.call(ctx),false);assert.equal(said.length,2);
  ctx.A11yWorldHudMode=()=>2;current.call(ctx);assert.equal(ctx.mA11yFirstPersonKnown,false);
});
test('a camera-toggle Tab cannot also enter HUD browsing; a later Tab still works',()=>{
  const {ctx,calls}=fixture();ctx.mA11yScope=null;ctx.mA11yFirstPersonFence=1350;
  tab.call(ctx,1);assert.deepStrictEqual(calls,[]);assert.equal(ctx.mA11yScope,null);
  clock.now=1400;tab.call(ctx,1);assert.deepStrictEqual(calls,[['option',1]]);
  assert.equal(ctx.mA11yHudBrowsing,true);clock.now=1000;
});
test('single-choice getter excludes composite dialogs and torn-down dialogs',()=>{
  const getter=method('A11ySingleSelection',fs.readFileSync(path.join(__dirname,'../flash/extra-classes/PickersMain.as'),'utf8'));
  const ctx={mDialogMsg:{dialog_type:1},mPickerData:{max_selectable:1}};
  assert.equal(getter.call(ctx),true);ctx.mPickerData.max_selectable=2;assert.equal(getter.call(ctx),false);
  ctx.mPickerData.max_selectable=1;ctx.mDialogMsg.dialog_type=9;assert.equal(getter.call(ctx),false);
  ctx.mDialogMsg=null;assert.equal(getter.call(ctx),false);
});
test('single-choice Enter uses the native enabled Done; multiselect and unselected rows never commit',()=>{
  const commit=method('A11yConfirmSinglePicker'),button={},root={btnDone:button,A11ySingleSelection:()=>true};
  const item={Selected:true,parent:root},clicked=[];
  const ctx={mA11yActiveModalRoot:root,mTooltipsLayer:{stage:{}},A11ySimplifiedActive:()=>true,
    A11yIsLive:()=>true,A11yPickerToggleCell:()=>true,A11yClickControl(target){clicked.push(target);return true;}};
  assert.equal(commit.call(ctx,item),true);assert.deepStrictEqual(clicked,[button]);
  clicked.length=0;root.A11ySingleSelection=()=>false;assert.equal(commit.call(ctx,item),false);assert.equal(clicked.length,0);
  root.A11ySingleSelection=()=>true;item.Selected=false;assert.equal(commit.call(ctx,item),false);assert.equal(clicked.length,0);
  item.Selected=true;ctx.A11yClickControl=()=>false;assert.equal(commit.call(ctx,item),false);
  ctx.A11yIsLive=()=>false;assert.equal(commit.call(ctx,item),false);
});
test('selection count uses native full-list selections and keeps original mode unchanged',()=>{
  const count=method('A11ySelectionCount');
  const ctx={A11ySimplifiedActive:()=>true,A11yPickerToggleCell:()=>true,A11yFindScrollList:()=>({}),
    A11yGridLayout:()=>({GetDataFeed:()=>({GetSelectedIndices:()=>[0,4,27]})})};
  assert.equal(count.call(ctx,{}),'3 selected');ctx.A11ySimplifiedActive=()=>false;assert.equal(count.call(ctx,{}),'');
});
test('save choices use native Load metadata and leave Save As and original mode alone',()=>{
  const choice=method('A11ySaveChoice'),ctx={A11ySimplifiedActive:()=>true};
  const row={kind:'widgets.General.SaveLoadMenu.controls::SaveSlotDetailed',btnPlay:{visible:true,enabled:false,AudioExt:{ElementName:'LoadGame'}}};
  assert.equal(choice.call(ctx,row),true); // unavailable saves remain readable; activation keeps native guards
  row.btnPlay.AudioExt.ElementName='SaveGame';assert.equal(choice.call(ctx,row),false);
  row.btnPlay.AudioExt.ElementName='LoadGame';ctx.A11ySimplifiedActive=()=>false;assert.equal(choice.call(ctx,row),false);
});
test('Options button bar is traversed into categories only in simplified mode',()=>{
  const composite=method('A11yCompositeRow'),bar={kind:'scaleform.clik.controls::ButtonBar'};
  const ctx={mA11ySimplifiedMenus:true,A11ySimplifiedActive:()=>true};
  assert.equal(composite.call(ctx,bar),true);ctx.mA11ySimplifiedMenus=false;assert.equal(composite.call(ctx,bar),false);
  ctx.mA11ySimplifiedMenus=true;ctx.A11ySimplifiedActive=()=>false;assert.equal(composite.call(ctx,bar),false);
});
test('stationary pointer cannot interrupt keyboard rows; physical movement restores hover',()=>{
  const hold=method('A11yHoldPointerSpeech'),ignore=method('A11yIgnoreStationaryHover');
  const stage={mouseX:420,mouseY:300};
  const ctx={mA11yKeyboard:true,mA11yFocused:{},mTooltipsLayer:{stage},
    A11ySimplifiedActive:()=>true,A11yIsLive:()=>true};
  hold.call(ctx);assert.equal(ignore.call(ctx),true);
  stage.mouseY=350;assert.equal(ignore.call(ctx),false);assert.equal(ctx.mA11yPointerSpeechHeld,false);
  stage.mouseY=300;assert.equal(ignore.call(ctx),false);
  hold.call(ctx);assert.equal(ignore.call(ctx),true);
  ctx.A11yIsLive=()=>false;assert.equal(ignore.call(ctx),false);
  ctx.A11yIsLive=()=>true;ctx.A11ySimplifiedActive=()=>false;assert.equal(ignore.call(ctx),false);
  hold.call(ctx);assert.equal(ctx.mA11yPointerSpeechHeld,false);
});
test('simplified traversal omits redundant Close, preserves Done and original-mode close',()=>{
  const decoration=method('A11yKeyboardDecoration');
  const ctx={mA11ySimplifiedMenus:true,A11ySimplifiedActive:()=>true,
    A11yTextDecoration:()=>false,A11yDialogCloseButton:()=>false};
  const button={name:'btnClose',kind:'olympus.gui.buttons::Button',parent:null};
  assert.equal(decoration.call(ctx,button),true);
  button.name='btnDone';assert.equal(decoration.call(ctx,button),false);
  button.name='btnClose';ctx.mA11ySimplifiedMenus=false;assert.equal(decoration.call(ctx,button),false);
  ctx.mA11ySimplifiedMenus=true;ctx.A11ySimplifiedActive=()=>false;assert.equal(decoration.call(ctx,button),false);
});
console.log(checks+' simplified menu checks passed');
