/* Execute production traversal and scope bodies against native-shaped fixtures. */
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm');
const fixture=fs.readFileSync(path.join(__dirname,'test_flash_navigation_v10.js'),'utf8');
const head=fixture.slice(0,fixture.indexOf('let passed = 0;'));
const checks=String.raw`
let passed=0;
function test(name,run){run();passed++;console.log('PASS '+name);}
function card(kind,fields){
 const row=new MovieClip('row',kind);row.focusable=true;
 for(const name of fields){row[name]=row.add(new MovieClip(name,'olympus.gui.buttons::Button'));row[name].focusable=true;row[name].activate=()=>{throw Error('No traversal activation');};}
 return row;
}
for(const [name,kind,fields] of [
 ['Social Bunny friend','widgets.Gameplay.SocialMedia::SocialMediaFriendCellView',['btnSendMessage','btnRemoveFriend']],
 ['Social Bunny feed','widgets.Gameplay.SocialMedia::SocialMediaFeedCellView',['btnReaction','btnAddFriend']],
 ['Social Bunny direct message','widgets.Gameplay.SocialMedia::SocialMediaMessageDMCellView',['btnReaction']],
 ['club','widgets.Gameplay.Clubs.ClubManagement.controls::ClubCellView',['btnDetails','btnAction']],
 ['Gallery subscription','widgets.Exchange.Subscriptions.controls::SubscriptionCellView',['btnFollow','btnBlock','btnUnblock']],
 ['rental unit','widgets.Gameplay.SimInfoHUD.HouseholdInfoVenuePanel.RentalUnit::RentalUnitCellView',['btnTravel','btnViewAgreement','btnFillVacancy']],
 ['household card','widgets.GameEntry.HouseholdPanel.controls::HouseholdPanelCellView',['btnUserHH','btnDelete','btnStoryProgression']]
])test(name+' retains summary and exposes only visible native actions',()=>{
 const ui=manager(),row=card(kind,fields),targets=[];ui.A11yCollectFocusables(row,targets,0);
 assert.deepStrictEqual(targets,[row,...fields.map(name=>row[name])]);
 row[fields[0]].visible=false;const hidden=[];ui.A11yCollectFocusables(row,hidden,0);assert(!hidden.includes(row[fields[0]]));
 row.visible=false;const none=[];ui.A11yCollectFocusables(row,none,0);assert.equal(none.length,0);
});
test('actual nested direct-message wrapper does not swallow the reaction action or duplicate text stops',()=>{
 const ui=manager(),outer=new MovieClip('message','widgets.Gameplay.SocialMedia::SocialMediaMessageCellView');outer.focusable=true;
 const dm=outer.add(card('widgets.Gameplay.SocialMedia::SocialMediaMessageDMCellView',['btnReaction']));outer.mcDirectMessage=dm;
 const targets=[];ui.A11yCollectFocusables(outer,targets,0);assert.deepStrictEqual(targets,[dm,dm.btnReaction]);
});
test('unrelated cell with similar child fields keeps the original traversal',()=>{
 const ui=manager(),row=card('unrelated::CellView',['btnReaction']);const targets=[];ui.A11yCollectFocusables(row,targets,0);assert.deepStrictEqual(targets,[row]);
});
test('Social Bunny action speaks its native author and post context with the localized tooltip',()=>{
 const messages=[];runtime.CommunicationManager={PostServerCommand:(name,payload)=>messages.push([name,decodeURIComponent(payload)])};
 const ui=manager(),row=card('widgets.Gameplay.SocialMedia::SocialMediaFeedCellView',['btnReaction']);
 row.txtSimName=row.add(new TextField('txtSimName','Alex'));row.txtPostContent=row.add(new TextField('txtPostContent','Native localized post'));
 row.btnReaction.TooltipExt={Text:'Native localized reaction label'};
 ui.A11yAnnounceDisplay(row.btnReaction,'a11y.focus_enc',true);
 assert(messages[0][1].includes('Alex'));assert(messages[0][1].includes('Native localized post'));assert(messages[0][1].includes('Native localized reaction label'));
});
test('goal icon is one readable stop and does not duplicate its decorative children',()=>{
 const ui=manager(),goal=new MovieClip('goal','widgets.Gameplay.SituationDisplay.controls::SituationGoalIconContainer');
 const child=goal.add(new MovieClip('decorativeIcon'));child.focusable=true;
 const stops=[];ui.A11yCollectFocusables(goal,stops,0);assert.deepStrictEqual(stops,[goal]);
});
test('native photo filters and venue cells announce their actual Selected property without enabling them',()=>{
 for(const kind of ['widgets.Gameplay.SimCamera.controls::CameraFilterCellView','widgets.Gameplay.SituationCreation.controls::LocationCellView']){
  const ui=manager();ui.A11yPickerToggleCell=()=>false;ui.A11yCheckboxState=method(tooltip.replace(/:\*/g,':Object'),'A11yCheckboxState');
  const cell=new MovieClip('cell',kind);cell.Selected=true;cell.enabled=false;
  assert.equal(ui.A11yCheckboxState(cell),'checked');assert.equal(cell.enabled,false);cell.Selected=false;assert.equal(ui.A11yCheckboxState(cell),'unchecked');
 }
});
let now=10000;
runtime.getTimer=()=>now;runtime.Event={ENTER_FRAME:'frame'};
function goalFixture(){
 const services=[],replies=[],listeners=new Map(),ui=manager();
 const root=new MovieClip('SituationDisplay'),tab=root.add(new MovieClip('tab')),content=tab.add(new MovieClip('event','widgets.Gameplay.SituationDisplay.controls::SituationContent'));
 content.Id='18446744073709551000';content.visible=false;
 const goals=content.add(new MovieClip('goals'));content.mSituationGoalDisplay=goals;
 tab.OpenContentPanelWithId=id=>{assert.equal(id,content.Id);content.visible=true;};
 ui.mTooltipsLayer={addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:(name,fn)=>listeners.delete(name)};
 Object.assign(ui,{mA11yKeyboard:true,mA11yKeyboardLease:999999,mA11yActiveModalRoot:null,mA11yStatusScope:null,mA11yScope:null,mA11yPendingScope:null,mA11yGoalContent:null,mA11yGoalScope:null,mA11yGoalCheck:0,
  A11yModalFrame(){},A11yEditing:()=>false,A11yLoadedWidget:name=>name==='SituationDisplay'?root:null,A11yWorldHudMode:()=>1,
  A11yIsLive:item=>{for(let n=item;n;n=n.parent)if(!n.visible||!n.stage)return false;return item!=null;},
  A11yFocusInto:scope=>{ui.mA11yPendingScope=scope;},A11yClearFocus:()=>{ui.cleared=true;},A11yPostToPython:(name,text)=>replies.push([name,decodeURIComponent(text)])});
 runtime.CommunicationManager={CallGameService:(name,data)=>{services.push([name,data]);if(name==='BBGetCurrentZoneId')return '9007199254740993';throw Error('Unexpected native action '+name);}};
 const scopeSource=tooltip.replace(/this\.A11yLoadedWidget\(([^)]*)\)\s+as\s+DisplayObject/g,'asCast(this.A11yLoadedWidget($1),DisplayObject)');
 for(const name of ['A11yEventGoalFind','A11yEventGoalClear','A11yEventGoalFrame','A11yEventGoals','A11yPhotography'])ui[name]=method(scopeSource,name);
 return {ui,root,tab,content,goals,services,replies,listeners};
}
function request(f,id=f.content.Id,zone='9007199254740993'){f.ui.A11yEventGoals(['A11y','eventgoals',id,zone,'7']);}
test('event goals opens the matching native event panel and scopes only its goals',()=>{
 const f=goalFixture();request(f);assert.equal(f.ui.mA11yStatusScope,f.goals);assert.equal(f.ui.mA11yPendingScope,f.goals);
 assert.deepStrictEqual(f.replies,[['a11y.eventgoals_enc','7|9007199254740993|opened']]);assert(f.services.every(([name])=>name==='BBGetCurrentZoneId'));assert.equal(f.listeners.size,1);
});
test('wrong event identity or zone never opens another event panel',()=>{
 for(const wrong of ['id','zone']){const f=goalFixture();request(f,wrong==='id'?'8':f.content.Id,wrong==='zone'?'8':'9007199254740993');assert.equal(f.content.visible,false);assert.equal(f.ui.mA11yStatusScope,null);assert(f.replies[0][1].endsWith('|unavailable'));}
});
test('a blocking modal prevents goal focus without closing the dialog',()=>{
 const f=goalFixture();f.ui.mA11yActiveModalRoot=new MovieClip('dialog');request(f);assert(f.replies[0][1].endsWith('|blocked'));assert.equal(f.content.visible,false);
});
test('editing or startup becoming active before the native reply prevents goal focus',()=>{
 for(const change of ['editing','startup']){
  const f=goalFixture();if(change==='editing')f.ui.A11yEditing=()=>true;else f.ui.mA11yStartupActive=true;
  request(f);assert(f.replies[0][1].endsWith('|blocked'));assert.equal(f.content.visible,false);assert.equal(f.listeners.size,0);
 }
});
test('event identity change or removal releases only the owned goal scope and listener',()=>{
 for(const change of ['id','visible','zone']){
  const f=goalFixture();request(f);f.ui.mA11yScope=f.goals;
  if(change==='id')f.content.Id='other';if(change==='visible')f.content.visible=false;
  if(change==='zone')runtime.CommunicationManager.CallGameService=()=> 'other';
  f.ui.A11yEventGoalFrame({});assert.equal(f.ui.mA11yStatusScope,null);assert.equal(f.ui.mA11yPendingScope,null);assert.equal(f.listeners.size,0);assert(f.ui.cleared);
 }
});
test('moving into another scope removes the observer without clearing the new modal focus',()=>{
 const f=goalFixture();request(f);const other=new MovieClip('other');f.ui.mA11yStatusScope=other;f.ui.mA11yScope=other;
 f.ui.A11yEventGoalFrame({});assert.equal(f.ui.mA11yScope,other);assert.equal(f.ui.mA11yStatusScope,other);assert.equal(f.listeners.size,0);
});
test('goal reader has a bounded lease and no persistent frame work after it ends',()=>{
 const f=goalFixture();request(f);now=400000;f.ui.A11yEventGoalFrame({});assert.equal(f.listeners.size,0);assert.equal(f.ui.mA11yGoalScope,null);now=10000;
});
function waitForGoalRows(f){
 runtime.Dictionary=function(){};
 Object.assign(f.ui,{mA11yScopeTries:0,mA11yScopeReadyAt:0,mA11yNavQueue:[],mA11yScopeHistory:[],mA11yAutoFocus:false,
  A11yIndexMotiveLinks(){},A11yFocusHover(){},A11yAnnounceScope(){f.announced=true;},A11yDrainNav(){}});
 f.ui.A11yScopeFrame=method(tooltip,'A11yScopeFrame');
}
test('a native goal row arriving during the normal wait still opens without unavailable feedback',()=>{
 const f=goalFixture();request(f);waitForGoalRows(f);
 for(let i=0;i<149;i++)f.ui.A11yScopeFrame({});
 assert.equal(f.ui.mA11yPendingScope,f.goals);assert.equal(f.replies.length,1);
 f.goals.add(new MovieClip('goal','widgets.Gameplay.SituationDisplay.controls::SituationGoalCellView'));
 f.ui.A11yScopeFrame({});
 assert.equal(f.ui.mA11yPendingScope,null);assert.equal(f.ui.mA11yScope,f.goals);
 assert.equal(f.ui.mA11yStatusScope,f.goals);assert(f.announced);assert.equal(f.replies.length,1);
});
test('a truly empty event releases only its own scope and reports unavailable once',()=>{
 const f=goalFixture();request(f);waitForGoalRows(f);
 const previous=new MovieClip('previous');f.ui.mA11yScope=previous;
 for(let i=0;i<151;i++)f.ui.A11yScopeFrame({});
 assert.equal(f.ui.mA11yPendingScope,null);assert.equal(f.ui.mA11yStatusScope,null);
 assert.equal(f.ui.mA11yGoalScope,null);assert.equal(f.ui.mA11yScope,previous);assert.equal(f.listeners.size,0);
 assert.deepStrictEqual(f.replies[1],['a11y.widget_enc','0|0|event goals unavailable']);
 f.ui.A11yScopeFrame({});assert.equal(f.replies.length,2);
});
test('empty photography and unrelated scopes retain their existing timeout behaviour',()=>{
 for(const kind of ['camera','other']){
  const f=goalFixture();request(f);waitForGoalRows(f);const other=new MovieClip(kind);
  if(kind==='camera')f.ui.mA11yGoalId='';else f.ui.mA11yPendingScope=other;
  const pending=f.ui.mA11yPendingScope;f.ui.mA11yScopeTries=150;f.ui.A11yScopeFrame({});
  assert.equal(f.ui.mA11yScope,pending);assert.equal(f.ui.mA11yPendingScope,null);
  assert.equal(f.ui.mA11yStatusScope,f.goals);assert.equal(f.replies.length,1);
 }
});
test('photography route focuses an already open camera without taking a photo',()=>{
 const f=goalFixture(),camera=new MovieClip('SimCamera');f.ui.A11yLoadedWidget=name=>name==='SimCamera'?camera:null;f.ui.mA11yActiveModalRoot=camera;
 f.ui.A11yPhotography();assert.equal(f.ui.mA11yStatusScope,camera);assert.equal(f.ui.mA11yPendingScope,camera);assert(f.services.every(([name])=>name==='BBGetCurrentZoneId'));
 camera.visible=false;f.ui.A11yEventGoalFrame({});assert.equal(f.listeners.size,0);
});
test('photography route does not open a camera or bypass another modal',()=>{
 const f=goalFixture();f.ui.A11yLoadedWidget=()=>null;f.ui.A11yPhotography();assert.equal(f.ui.mA11yStatusScope,null);
 const camera=new MovieClip('SimCamera');f.ui.A11yLoadedWidget=()=>camera;f.ui.mA11yActiveModalRoot=new MovieClip('other');f.ui.A11yPhotography();assert.equal(f.ui.mA11yStatusScope,null);
});

test('Social Bunny and event-goal summaries are read-only; Enter does not guess a native action',()=>{
 for(const kind of ['widgets.Gameplay.SocialMedia::SocialMediaFriendCellView','widgets.Gameplay.SocialMedia::SocialMediaFeedCellView','widgets.Gameplay.SocialMedia::SocialMediaMessageDMCellView','widgets.Gameplay.SituationDisplay.controls::SituationGoalIconContainer']){
  const ui=manager(),row=new MovieClip('row',kind),spoken=[];
  Object.assign(ui,{mA11yKeyboard:true,mA11yIdxDir:0,mA11yPendingScope:null,mA11yFocused:row,A11yModalFrame(){},A11ySeasonActivate:()=>false,A11yActivateCASName:()=>false,A11yIsLive:()=>true,A11yActionProxy:item=>item,A11yAnnounceDisplay:item=>spoken.push(item),A11ySafeDispatch:()=>{throw Error('Summary must not click');}});
  ui.A11yActivate=method(tooltip,'A11yActivate');ui.A11yActivate();assert.deepStrictEqual(spoken,[row]);
 }
});
test('real native child buttons still receive one mouse click sequence on explicit Enter',()=>{
 const ui=manager(),button=new MovieClip('btnSendMessage','olympus.gui.buttons::Button'),events=[];
 Object.assign(ui,{mA11yKeyboard:true,mA11yIdxDir:0,mA11yPendingScope:null,mA11yFocused:button,A11yModalFrame(){},A11ySeasonActivate:()=>false,A11yActivateCASName:()=>false,A11yIsLive:()=>true,A11yActionProxy:item=>item,A11yPickerFooter:()=>false,A11yInventoryMenu:()=>false,A11yPickerToggleCell:()=>false,A11ySafeDispatch:(item,event)=>events.push(event)});
 runtime.MouseEvent={MOUSE_DOWN:'down',MOUSE_UP:'up',CLICK:'click'};
 ui.A11yActivate=method(tooltip,'A11yActivate');ui.A11yActivate();assert.deepStrictEqual(events,['down','up','click']);
});


test('book-style native title and description rows expose real fields and retain the confirm footer',()=>{
 const ui=manager(),dialog=new MovieClip('dialog','widgets.Dialog.dialogs::TextInputDialog'),fields=[];
 for(const kind of ['widgets.Dialog.controls::TextInputCellView','widgets.Dialog.controls::InlineTextInputCellView']){
  const row=dialog.add(new MovieClip('row',kind));row.focusable=true;
  row.txtLabel=row.add(new TextField('txtLabel',kind.includes('Inline')?'Native description label':'Native title label'));
  const component=row.add(new MovieClip('mcTextInput','scaleform.clik.controls::TextInput'));
  const field=component.add(new TextField('textField','Existing text'));field.type='input';field.focusable=true;fields.push(field);
 }
 const confirm=dialog.add(new MovieClip('btnConfirm','olympus.gui.buttons::Button'));confirm.focusable=true;confirm.enabled=false;
 const targets=[];ui.A11yCollectFocusables(dialog,targets,0);assert.deepStrictEqual(targets,[...fields,confirm]);assert.equal(confirm.enabled,false);
 const messages=[];runtime.CommunicationManager={PostServerCommand:(name,text)=>messages.push(decodeURIComponent(text))};ui.A11yAnnounceDisplay(fields[0],'a11y.focus_enc',true);assert(messages[0].includes('Native title label'));assert(messages[0].includes('Existing text'));
});

console.log(passed+' requested and proactive UI checks passed (native runtime mocked).');
`;
vm.runInNewContext(head+checks,{require,__dirname,__filename,console},{filename:'requested-ui-fixtures'});
