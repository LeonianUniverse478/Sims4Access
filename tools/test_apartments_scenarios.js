'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm');
const fixture=fs.readFileSync(path.join(__dirname,'test_flash_navigation_v10.js'),'utf8');
const head=fixture.slice(0,fixture.indexOf('let passed = 0;'));
const checks=String.raw`
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
const messages=[];runtime.CommunicationManager={PostServerCommand:()=>{},SendUIMessage:(name,data)=>messages.push([name,data])};
const native=fs.readFileSync(path.join(root,'flash/extra-classes/PlexLotSelectOverlay.as'),'utf8');
const nativeTyped=native.replace(/:MouseEventEx\b/g,':MovieClip').replace(/:uint\b/g,':int').replace(/\buint\(/g,'int(').replace(/clip is PlexClip/g,'clip is MovieClip').replace(/clip as PlexClip/g,'clip as DisplayObject').replace('protected function OnClickImage','public function OnClickImage').replace(/param1 as MouseEventEx/g,'asCast(param1,MovieClip)');
runtime.ArrayUtils={IndexOfByFieldName:(list,key,id)=>list.findIndex(x=>x[key]===id)};
function overlay(){
 const panel=new MovieClip('overlay','widgets.GameEntry.Dock.controls::PlexLotSelectOverlay');
 panel.mLotDataList=[{plexId:12,lotName:'19 Culpepper House',lotDescriptionData:{name:{toString:()=> 'Native fallback'}}}];
 const clip=panel.add(new MovieClip('unit','widgets.GameEntry.Dock.controls::PlexClip'));clip.mouseEnabled=false;
 panel.mPlexIdToClipMap={12:{plexClip:clip,enabled:true}};panel.mCurrentLevel=2;panel.mSelectedPlexId=0;panel.mOverPlexId=0;
 panel.GetPlexIDForClip=item=>item===clip?12:0;panel.SetOverPlexId=id=>{panel.mOverPlexId=id;};panel.SetSelectedPlexId=id=>{panel.mSelectedPlexId=id;};
 panel.OnClickImage=method(nativeTyped,'OnClickImage');panel.A11yPlexInfo=method(nativeTyped,'A11yPlexInfo');panel.A11yPlexSelect=method(nativeTyped,'A11yPlexSelect');return {panel,clip};
}
test('scenario group exposes the card and native Play button without activating either',()=>{
 const ui=manager(),group=new MovieClip('group','widgets.shared.controls.Scenarios::ScenarioDisplayGroupCellView');group.focusable=true;
 group.mcGrid=group.add(new MovieClip('mcGrid'));const card=group.mcGrid.add(new MovieClip('card','widgets.shared.controls.Scenarios::ScenarioCardCellView'));card.focusable=true;
 card.btnPlay=card.add(new MovieClip('btnPlay','olympus.gui.buttons::Button'));card.btnPlay.focusable=true;
 const found=[];ui.A11yCollectFocusables(group,found,0);assert.deepStrictEqual(found,[card,card.btnPlay]);
 card.btnPlay.visible=false;const hidden=[];ui.A11yCollectFocusables(group,hidden,0);assert.deepStrictEqual(hidden,[card]);
});
test('scenario native name difficulty description roles requirements goals and Play context are narrated',()=>{
 const ui=manager(),card=new MovieClip('card','widgets.shared.controls.Scenarios::ScenarioCardCellView');
 for(const [key,value] of Object.entries({txtName:'Native scenario',txtDifficulty:'Native difficulty',txtDescription:'Native description',txtRewardName:'Native reward'}))card[key]=card.add(new TextField(key,value));
 card.ScenarioData={roles:['Native role'],requirements:[{toString:()=> 'Native requirement'}],goals:[{toString:()=> 'Native goal'}]};
 const play=card.add(new MovieClip('btnPlay'));play.add(new TextField('label','Native Play'));
 const result=[];ui.A11yScenarioText(play,result);for(const word of ['scenario','difficulty','description','reward','role','requirement','goal','Play'])assert(result.some(x=>x.includes('Native '+word)));
});
test('unrelated card data cannot replace another screen announcement',()=>{
 const ui=manager(),item=new MovieClip('card','unrelated');item.ScenarioData={roles:['wrong']};const result=['keep'];ui.A11yScenarioText(item,result);assert.deepStrictEqual(result,['keep']);
});
test('apartment helper selects exactly its native clip through EA OnClickImage',()=>{
 messages.length=0;const {panel,clip}=overlay();assert.equal(panel.A11yPlexSelect(clip),true);assert.equal(messages.length,1);assert.equal(messages[0][0],'LotSelected');assert.equal(messages[0][1].lotData,panel.mLotDataList[0]);
 assert.equal(panel.A11yPlexSelect(clip),true);assert.equal(messages.length,1,'already selected unit does not select twice');
});
test('disabled and hidden apartments cannot trigger native selection',()=>{
 for(const mode of ['disabled','hidden','closed']){messages.length=0;const {panel,clip}=overlay();if(mode==='disabled')panel.mPlexIdToClipMap[12].enabled=false;if(mode==='hidden')clip.visible=false;if(mode==='closed')panel.visible=false;assert.equal(panel.A11yPlexSelect(clip),false);assert.equal(messages.length,0);}
});
test('stale apartment marker and missing native data never choose a different unit',()=>{
 const {panel,clip}=overlay();messages.length=0;panel.mLotDataList=[];assert.equal(panel.A11yPlexSelect(clip),false);assert.equal(messages.length,0);
});
test('shared apartment walker exposes mouse-disabled markers and localized native lot names',()=>{
 const ui=manager(),{panel,clip}=overlay();const found=[];ui.A11yCollectFocusables(panel,found,0);assert(found.includes(clip));assert.equal(ui.A11yMapLabel(clip),'19 Culpepper House');panel.mLotDataList[0].lotName='';assert.equal(ui.A11yMapLabel(clip),'Native fallback');
});
test('shared apartment activation respects another blocking surface',()=>{
 const ui=manager(),{panel,clip}=overlay();ui.A11yIsLive=()=>true;ui.mA11yActiveModalRoot=new MovieClip('other dialog');messages.length=0;assert.equal(ui.A11yPlexActivate(clip),true);assert.equal(messages.length,0);
});
test('Enter reaches the native unit selector before the marker mouse-disabled guard',()=>{
 const ui=manager(),{panel,clip}=overlay();Object.assign(ui,{mA11yKeyboard:true,mA11yFocused:clip,mA11yIdxDir:0,mA11yPendingScope:null,mA11yActiveModalRoot:null,A11yModalFrame:()=>{},A11ySeasonActivate:()=>false,A11yActivateCASName:()=>false,A11yIsLive:()=>true});
 ui.A11yActivate=method(tooltip,'A11yActivate');messages.length=0;ui.A11yActivate();assert.equal(messages.length,1);assert.equal(messages[0][0],'LotSelected');
});
test('Enter on a scenario summary reads it without starting that scenario',()=>{
 const ui=manager(),card=new MovieClip('card','widgets.shared.controls.Scenarios::ScenarioCardCellView');let read=0;
 Object.assign(ui,{mA11yKeyboard:true,mA11yFocused:card,mA11yIdxDir:0,mA11yPendingScope:null,mA11yActiveModalRoot:null,A11yModalFrame:()=>{},A11ySeasonActivate:()=>false,A11yActivateCASName:()=>false,A11yIsLive:()=>true,A11yActionProxy:x=>x,A11yAnnounceDisplay:()=>read++});
 ui.A11yActivate=method(tooltip,'A11yActivate');messages.length=0;ui.A11yActivate();assert.equal(read,1);assert.equal(messages.length,0);
});
test('rental property region and building wrappers expose expand and individual unit actions',()=>{
 const ui=manager(),region=new MovieClip('region','widgets.Gameplay.SimInfoHUD.HouseholdInfoVenuePanel.RentalUnit::RentalUnitRegionCellView');region.focusable=true;
 region.btnExpander=region.add(new MovieClip('btnExpander','olympus.gui.buttons::Button'));region.btnExpander.focusable=true;
 region.mcLotGrid=region.add(new MovieClip('mcLotGrid'));const lot=region.mcLotGrid.add(new MovieClip('lot','widgets.Gameplay.SimInfoHUD.HouseholdInfoVenuePanel.RentalUnit::RentalUnitLotCellView'));lot.focusable=true;
 lot.btnSellBusiness=lot.add(new MovieClip('btnSellBusiness','olympus.gui.buttons::Button'));lot.btnSellBusiness.focusable=true;lot.mcUnitGrid=lot.add(new MovieClip('mcUnitGrid'));
 const unit=lot.mcUnitGrid.add(new MovieClip('unit','widgets.Gameplay.SimInfoHUD.HouseholdInfoVenuePanel.RentalUnit::RentalUnitCellView'));unit.focusable=true;
 for(const key of ['btnTravel','btnViewAgreement','btnFillVacancy']){unit[key]=unit.add(new MovieClip(key,'olympus.gui.buttons::Button'));unit[key].focusable=true;}
 const targets=[];ui.A11yCollectFocusables(region,targets,0);assert.deepStrictEqual(targets,[region.btnExpander,lot.btnSellBusiness,unit,unit.btnTravel,unit.btnViewAgreement,unit.btnFillVacancy]);
 region.mcLotGrid.visible=false;const collapsed=[];ui.A11yCollectFocusables(region,collapsed,0);assert.deepStrictEqual(collapsed,[region.btnExpander]);
});
console.log(count+' apartment and scenario checks passed (native runtime mocked).');
`;
vm.runInNewContext(head+'\n'+checks,{require,__dirname,console},{filename:'apartment-scenario-fixtures'});
