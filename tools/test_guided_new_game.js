'use strict';
// Guided New Game: once a new family's Create a Sim is ready (CASNameField
// live, no questionnaire, CasIsNewFamily), the guide opens EA dialogs
// (DialogManager.RequestDialog with LocalRequestData and a DialogContainer)
// that hold only buttons, and applies each choice through the CAS game
// services EA's own panels call:
//   name: CAS's own editor (CASNameFieldSetEditMode) or CASRandomizeSimName
//   age: GetAgesData / SetSimAge + RefreshSimAgeGender (babies left out)
//   gender: SetSimGender toggles, as the age/gender panel does
//   traits: GetTraitGroups / GetAllSimTraitsInfo, AddTraitToSim, RemoveTraitFromSim,
//           up to maxTraits, leaving out chosen and clashing traits
//   aspiration: CasGetAspirationCategories / CasGetAspirationTracksByCategory,
//               SetSimAspiration {uid}
// Version 1's text boxes in our dialog were not keyboard-usable (live
// 2026-10-13); version 2's buttons-only name step worked live. No CAS movie
// is rebuilt; added code follows GFX-SAFETY.
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
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1').replace(/\s+as\s+(Class|Array|DisplayObject|Object)\b/g,'').replace(/ is (\w+) \?/g,' instanceof $1 ?');
 return vm.runInNewContext('(function('+strip(args).replace(/\s*=\s*[^,]+/g,'')+'){'+strip(code)+'})',ctx);
}
// Objects built inside the vm sandbox have another realm's prototypes.
const same=(a,b,m)=>assert.strictEqual(JSON.stringify(a),JSON.stringify(b),m);
let checks=0;
const YA=16,ADULT=32,TEEN=8,BABY=1,FEMALE=8192,MALE=4096;
function world(over){
 const w=Object.assign({cas:true,story:false,storyMode:false,newFamily:true,first:'Ann',last:'Lee',now:0,age:ADULT,gender:MALE,
  traits:['t_cheer'],maxTraits:3,aspiration:null},over||{});
 const shown=[],ui=[],marks=[],said=[],calls=[],listeners={},clicks=[];
 w.id=w.id||'77';w.house=[w];w.cur=0;w.rels={};const c=()=>w.house[w.cur];
 const lot=(id,name,type,house,furn,land,beds,baths)=>{const o={zoneInstanceId:id,lotName:name,mLotType:type,IsInPlex:false,IsMultiUnitBuilding:false,
  set(h,f,b1,b2){house=h;furn=f;Object.assign(o,{IsEmpty:h===0&&f===0,IsFurnished:f!==0,TotalPrice:land+h+f,UnfurnishedPrice:land+h,LotPrice:land,numBeds:b1,numBaths:b2});},
  UpdateZoneData(z){o.updated=true;o.set(z.raw.housePrice,z.raw.furnishingsPrice,z.raw.numBeds,z.raw.numBaths);}};o.set(house,furn,beds,baths);return o;};
 const nhds={n1:{regionId:'r_wc',name:'Pinecrest',IsPlayerFacingNeighborhood:true,lots:[lot('z1','Garden Essence',0,15000,3000,2000,2,1),lot('z2','Big Villa',0,60000,20000,5000,4,3),lot('z3','Library',3,1,1,1,0,0),lot('z4','Goth Manor',1,1,1,1,3,2)]},
  n2:{regionId:'r_wc',name:'Oakenstead',IsPlayerFacingNeighborhood:true,lots:[lot('z5','Empty Plot',0,0,0,4000,0,0)]},
  n3:{regionId:'r_os',name:'Desert Bloom',IsPlayerFacingNeighborhood:true,lots:[]},
  n4:{regionId:'r_gf',name:'Granite Falls',IsPlayerFacingNeighborhood:true,lots:[lot('z9','Cabin',0,1,1,1,1,1)]},
  n5:{regionId:'r_hidden',name:'Hidden',IsPlayerFacingNeighborhood:false,lots:[]}};
 const regions={r_wc:{regionName:{text:'Willow Creek'},bVacationWorld:false},r_os:{regionName:{text:'Oasis Springs'},bVacationWorld:false},r_gf:{regionName:{text:'Granite Falls'},bVacationWorld:true}};
 const dropdown={visible:true,DropdownExt:{SelectedData:null,SetSelectedFromMenuItemData(d){calls.push(['furnish',d]);this.SelectedData={data:d};}},dispatchEvent(e){calls.push(['dropdownEvent',e.type,e.data.data]);}};
 const movePanel={__cls:'widgets.GameEntry.MovePanel.controls::MoveInPanel',ddInOptions:dropdown,btnOkay:{name:'okay',enabled:true},btnClose:{name:'close'}};
 const moveWidget={numChildren:2,getChildAt:i=>[{__cls:'Other'},movePanel][i]};
 const worldWidget={mcWSGridView:{},mouseChildren:true};
 const season={btnSpring:{name:'btnSpring'},btnSummer:{name:'btnSummer'},btnFall:{name:'btnFall'},btnWinter:{name:'btnWinter'}};
 const nameField={btnTextEffect:{visible:true}};
 w.funds=w.funds===undefined?20000:w.funds;w.season=false;w.worldUp=false;w.move=false;
 class LocalRequestData{constructor(){this.actions=[];this.inputs=[];}}
 class CallbackDialogAction{constructor(fn,params,label){this.fn=fn;this.params=params;this.label=label;}}
 class DialogContainer{} class TitleBodyHeader{} class DialogButtonFooter{}
 class DialogRequest{constructor(dialog,data){this.dialog=dialog;this.data=data;}}
 class LocKey{constructor(raw){this.raw=raw;}toString(){return this.raw&&this.raw.text||'';}}
 const loc=t=>({text:t});
 const groups=[{groupId:1,title:loc('Emotional')},{groupId:2,title:loc('Hobby')}];
 const traitDefs={1:[['t_cheer','Cheerful',['t_gloomy']],['t_gloomy','Gloomy',['t_cheer']],['t_hot','Hot-Headed',[]],['t_walk','Walkstyle',[],'3']],2:[['t_art','Art Lover',[]],['t_geek','Geek',[]]]};
 const tracks={c1:[{id:'a_love'},{id:'a_secret'}],c2:[{id:'a_wealth'}]};
 const trackData={a_love:{uid:'a_love',display_text:loc('Soulmate'),isHiddenUnlockable:false},a_secret:{uid:'a_secret',display_text:loc('Hidden'),isHiddenUnlockable:true},
  a_wealth:{uid:'a_wealth',display_text:loc('Fabulously Wealthy'),isHiddenUnlockable:false}};
 const defs={'widgets.Dialog.data.LocalRequestData':LocalRequestData,'widgets.Dialog.actions.CallbackDialogAction':CallbackDialogAction,
  'widgets.Dialog.dialogs.DialogContainer':DialogContainer,'widgets.Dialog.footers.DialogButtonFooter':DialogButtonFooter,
  'widgets.Dialog.headers.TitleBodyHeader':TitleBodyHeader,'olympus.dialog.DialogRequest':DialogRequest,
  'olympus.dialog.DialogManager':{RequestDialog:r=>shown.push(r)},'olympus.localization.LocKey':LocKey,
  'gamedata.shared.SimGenderTypes':{MALE,FEMALE,GetGenderStringKey:(g)=>new LocKey(loc(g===FEMALE?'Female':'Male'))},
  'gamedata.Gameplay.shared.definitions.AspirationTrackStaticData':{GetTrackData:id=>trackData[id]},
  'gamedata.GameEntry.shared.NeighborhoodStateData':{get AllNeighborhoodData(){return w.worldUp?nhds:null;}},
  'gamedata.GameEntry.shared.RegionDescription':{GetRegionDescription:id=>regions[id]||null},
  'widgets.shared.constants.SimRelationship':{NONE:6,GetRelationshipName:(r)=>new LocKey(loc({6:'No relation',7:'Parent',8:'Sibling',9:'Spouse'}[r]))},
  'gamedata.CAS.Relationships.SimTropeItem':{ALL_TROPE_TYPES:2},
  'gamedata.GameEntry.Neighborhood.NeighborhoodLotData':class{constructor(raw){this.raw=raw;}},
  'olympus.gui.events.DropdownEvent':Object.assign(class{constructor(type,data){this.type=type;this.data=data;}},{ITEM_SELECTED:'itemSelected'})};
 const services={GetInCasStoryMode:()=>w.storyMode,CasIsNewFamily:()=>w.newFamily,
  CASGetSimInfo:()=>({firstName:c().first,lastName:c().last,simId:c().id,speciesType:1,maxTraits:c().maxTraits,voiceActor:c().voice||1,voicePitch:c().pitch||0}),
  GetSimAge:()=>c().age,GetSimGender:()=>c().gender,GetSimSpecies:()=>1,
  GetAgesData:a=>{calls.push(['ages',a]);return [BABY,128,2,4,TEEN,YA,ADULT,64].map(t=>({ageType:t,name:loc({1:'Baby',128:'Infant',2:'Toddler',4:'Child',8:'Teen',16:'Young Adult',32:'Adult',64:'Elder'}[t])}));},
  SetSimAge:a=>{calls.push(['setAge',a]);c().age=a;},SetSimGender:()=>{calls.push(['toggleGender']);c().gender=c().gender===MALE?FEMALE:MALE;},
  GetTraitGroups:()=>groups,
  GetAllSimTraitsInfo:a=>{assert.strictEqual(a.simId,c().id);return traitDefs[a.groupId].map(([id,t,c,type])=>({id,title:loc(t),equipped:false,conflictingTraitIds:c,type:type||'0'}));},
  CasGetEquippedTraits:()=>c().traits.slice(),CasPersonalityTraitsUIOpened:()=>calls.push(['traitsOpen']),CasPersonalityTraitsUIDone:()=>calls.push(['traitsDone']),
  GetVoicesDataForAgeSpecies:a=>{calls.push(['voices',a.species,a.age]);return [{tooltip:loc('Sweet'),minPitch:-1,maxPitch:1},{tooltip:loc('Melodic'),minPitch:-2,maxPitch:2},{tooltip:loc('Lilted'),minPitch:-1,maxPitch:1}];},
  SetSimVoiceActor:i=>{calls.push(['voice',i]);c().voice=i+1;},SetSimVoicePitch:a=>{calls.push(['pitch',a.value,a.slider_mouse_up]);c().pitch=a.value;},
  CasGetWalkCycleTraits:a=>{assert.strictEqual(a.simId,c().id);return [{id:'w1',title:loc('Default'),equipped:(c().walk||'w1')==='w1'},{id:'w2',title:loc('Swagger'),equipped:c().walk==='w2'}];},
  CasSetWalkCycleTrait:a=>{calls.push(['walk',a.traitID]);c().walk=a.traitID;},
  CasAddSim:a=>{calls.push(['addSim',a.relationship,a.species,a.occultType,a.action]);const n={id:String(78+w.house.length),first:'Bo',last:'Lee',age:ADULT,gender:FEMALE,traits:[],maxTraits:3,aspiration:null};
   w.house.push(n);if(!w.slowAdd){w.cur=w.house.length-1;}else{w.pending=w.house.length-1;}},
  CasSelectSim:i=>{calls.push(['select',i]);if(i<0||i>=w.house.length)return false;w.cur=i;return true;},
  CasGetHouseholdRelationsForCurrentSim:()=>w.house.map((o,i)=>({o,i})).filter(x=>x.i!==w.cur).map(x=>({simId:x.o.id,simIndex:x.i,age:x.o.age,speciesType:1,canModify:true,
   relOptions:[6,7,8,9],currentRelation:w.rels[[c().id,x.o.id].sort().join('-')]||6})),
  CasAddRelationship:a=>{calls.push(['rel',a.simIdA,a.simIdB,a.relType]);w.rels[[a.simIdA,a.simIdB].sort().join('-')]=a.relType;},
  CasSetTropeToRelationshipWith:a=>calls.push(['trope',a.tropeType]),
  GetNeighborhoodLotData:z=>{calls.push(['lotData',z]);return w.fresh&&w.fresh[z]||null;},
  AddTraitToSim:a=>{calls.push(['add',a.traitID]);c().traits.push(a.traitID);},RemoveTraitFromSim:a=>{calls.push(['remove',a.traitID]);c().traits=c().traits.filter(x=>x!==a.traitID);},
  CasGetAspirationCategories:()=>[{uid:'c2',name:loc('Fortune'),ui_sort_order:2},{uid:'c1',name:loc('Love'),ui_sort_order:1}],
  CasGetAspirationTracksByCategory:a=>tracks[a.categoryId],
  CASCheckProfanityOnSimNames:()=>({simId:w.rude?'77':'0'}),CasGetHouseholdExchangeData:()=>({name:'Lee'}),
  CasSaveHouseholdToTray:a=>calls.push(['tray',a.name]),EnterGame:a=>calls.push(['enter',a.name]),
  GetFamilyInfo:()=>({familyFunds:w.funds,familyId:'h1',familyLotId:'z1'}),PlayHousehold:a=>calls.push(['play',a.householdId,a.zoneInstanceId]),SetSimAspiration:a=>{calls.push(['aspiration',a.uid]);c().aspiration=a.uid;}};
 const ctx={Math:Math,getQualifiedClassName:o=>o&&o.__cls||'',getDefinitionByName:n=>{assert(n in defs,n);return defs[n];},getTimer:()=>w.now,Error:Error,String:String,int:v=>v|0,uint:v=>v>>>0,
  Array:Array,encodeURIComponent:encodeURIComponent,
  CommunicationManager:{CallGameService:(n,a)=>{assert(n in services,n);return services[n](a);},
   CallUIService:(n,a)=>n==='CasApplyNameFields'?true:false,
   AddMessageListenerByName:(n,f,o)=>{assert.strictEqual(o,'A11yGuide');listeners[n]=f;},RemoveMessageListenerByName:(n,f,o)=>{assert.strictEqual(o,'A11yGuide');delete listeners[n];},
   SendUIMessage:(n,a)=>{ui.push([n,a]);if(n==='CASRandomizeSimName'){c().first='Mira';c().last='Stone';}}}};
 const tm={mA11yGuideState:'',mA11yGuideReadyAt:0,mA11yGuideCheckAt:0,mA11yGuideDialogId:'',mA11yGuideSerial:0,mA11yGuideEditSeen:false,
  mA11yGuideEditAt:0,mA11yGuideList:[],mA11yGuideAspiration:'',mA11yGuideTraitsOpen:false,mA11yGuidePhase:'',mA11yGuidePhaseAt:0,mA11yGuideMapAt:0,mA11yGuideHousehold:'',mA11yGuideRegion:'',mA11yGuideLot:null,mA11yGuideFurnish:-1,mA11yGuideFresh:{},mA11yGuideNames:{},mA11yGuideNewSim:false,mA11yGuideAddFrom:'',mA11yManagedDialog:null,A11yIsLive:o=>!!o,
  A11yLoadedWidget:n=>n==='CASNameField'&&w.cas?nameField:n==='GameEntryWorldSelection'&&w.worldUp?worldWidget:n==='GameEntryMovePanel'&&w.move?moveWidget:null,
  A11ySeasonScope:()=>w.season?season:null,A11ySeasonActivate:(b,c)=>{calls.push(['season',b.name,c]);return true;},
  A11yClickControl:b=>{clicks.push(b.name);return true;},A11yCASStoryScope:()=>w.story?{}:null,
  A11yPostToPython:(c,p)=>c==='a11y.mark'?marks.push(p):said.push(decodeURIComponent(p))};
 for(const n of ['A11yGuideFrame','A11yGuideDialog','A11yGuideAnswer','A11yGuideList','A11yGuideText','A11yGuideSay','A11yGuideIntro','A11yGuideSimInfo',
   'A11yGuideSimName','A11yGuideNameDialog','A11yGuideTypeName','A11yGuideRandomName','A11yGuideNameResult','A11yGuideNoEditor','A11yGuideAgeDialog',
   'A11yGuideSetAge','A11yGuideRefreshAgeGender','A11yGuideGenderDialog','A11yGuideSetGender','A11yGuideTraitScan','A11yGuideEquippedIds','A11yGuideEquipped',
   'A11yGuideTraitsOpen','A11yGuideTraitsClose',
   'A11yGuideTraitsDialog','A11yGuideTraitGroupsDialog','A11yGuideTraitListDialog','A11yGuideTraitRemoveDialog','A11yGuideAspirationCategories',
   'A11yGuideAspirationTracks','A11yGuideSummary','A11yGuideFinish','A11yGuideReady','A11yGuideHomeStart','A11yGuideHomeError','A11yGuideHomeSave',
   'A11yGuideHomeSaved','A11yGuideHomeEnter','A11yGuideHomeFrame','A11yGuideSeasonDialog','A11yGuideWorlds','A11yGuideFunds','A11yGuideMoney','A11yGuideHomes',
   'A11yGuideWorldDialog','A11yGuideGoToWorld','A11yGuideMapLoaded','A11yGuideHomeLabel','A11yGuideLotsDialog','A11yGuideFurnishDialog','A11yGuideBuy',
   'A11yGuideMovePanel','A11yGuideMoveIn','A11yGuidePlayDialog','A11yGuidePlay','A11yGuideHomeAnswer','A11yGuideFailed','A11yGuideRemember','A11yGuideRelations',
   'A11yGuideOtherName','A11yGuideRelationName','A11yGuideAddSim','A11yGuideRelationsDialog','A11yGuideRelationPickDialog','A11yGuideSetRelation','A11yGuideSwitchDialog','A11yGuideSwitchTo','A11yGuideVoices','A11yGuideVoiceName','A11yGuideWalkStyles','A11yGuideExtrasDialog','A11yGuideVoiceDialog',
   'A11yGuidePitchDialog','A11yGuideWalkDialog']){
  const f=method(n,ctx);tm[n]=(...a)=>f.apply(tm,a); // AS3 method closures are bound
 }
 return {c,w,tm,shown,ui,marks,said,calls,listeners,clicks,nhds,movePanel,nameField,tick(ms){w.now=w.now+(ms||600);tm.A11yGuideFrame();}};
}
const last=t=>t.shown[t.shown.length-1].data;
const labels=t=>last(t).actions.map(a=>a.label);
function press(t,label){const a=last(t).actions.find(x=>x.label===label);assert(a,label+' in '+labels(t).join(' / '));a.fn(Object.assign({},a.params));}
function started(over){const t=world(over);t.tick();t.tick(1100);press(t,'Start');return t;}
{const t=world({storyMode:true});t.tick();t.tick();t.tick();assert.strictEqual(t.shown.length,0,'not during the questionnaire');
 t.w.storyMode=false;t.tick();assert.strictEqual(t.shown.length,0,'waits for CAS to settle');t.tick(1100);
 assert.strictEqual(t.shown.length,1);same(t.marks,['guide-offered']);
 assert.strictEqual(last(t).title,'Create your Sim');same(labels(t),['Start','Skip the guide and use the full Create a Sim screen']);
 assert.strictEqual(last(t).inputs.length,0,'buttons only');t.tick(1100);assert.strictEqual(t.shown.length,1,'shown once');checks++;}
{const t=world({newFamily:false});t.tick();t.tick(1100);assert.strictEqual(t.shown.length,0);same(t.marks,['guide-skip-not-new-family']);checks++;}
{const t=started();assert.strictEqual(last(t).title,'Step 1: Name');assert(last(t).promptText.startsWith('Your Sim is called Ann Lee right now.'));
 same(labels(t),['Type the name','Random name','Keep this name','Back']);
 press(t,'Type the name');same(t.ui,[['CASNameFieldSetEditMode',{bEditMode:true}]]);assert.strictEqual(t.tm.mA11yGuideState,'editing');
 assert(t.said[0].startsWith('0|0|Name boxes open.'),'spoken through a11y.speak_enc');const before=t.shown.length;
 t.nameField.btnTextEffect.visible=false;t.tick(300);t.tick(300);assert.strictEqual(t.shown.length,before,'waits while the editor is open');
 t.w.first='Kim';t.w.last='Fields';t.nameField.btnTextEffect.visible=true;t.tick(300);
 assert.strictEqual(last(t).title,'Name: Kim Fields');same(labels(t),['Next','Change the name']);checks++;}
{const t=started();press(t,'Random name');same(t.ui,[['CASRandomizeSimName',{overrideCurrent:true}]]);assert.strictEqual(last(t).title,'Name: Mira Stone');
 press(t,'Change the name');press(t,'Keep this name');assert.strictEqual(last(t).title,'Name: Mira Stone');checks++;}
{const t=started();press(t,'Type the name');t.tick(1000);t.tick(1000);t.tick(1200);assert.strictEqual(last(t).title,'Name boxes did not open');
 press(t,'OK');assert.strictEqual(last(t).title,'Step 1: Name');checks++;}
{const t=started();press(t,'Keep this name');press(t,'Next');
 assert.strictEqual(last(t).title,'Step 2: Age');same(labels(t),['Infant','Toddler','Child','Teen','Young Adult','Adult (now)','Elder','Back'],'no babies, youngest first');
 press(t,'Young Adult');same(t.calls.filter(c=>c[0]==='setAge'),[['setAge',YA]]);
 const refresh=t.ui.find(u=>u[0]==='RefreshSimAgeGender');same(refresh,['RefreshSimAgeGender',{simAge:YA,simGender:MALE,simSpecies:1}]);
 assert.strictEqual(last(t).title,'Step 3: Gender');same(labels(t),['Female','Male (now)','Back']);
 press(t,'Male (now)');assert.strictEqual(t.calls.filter(c=>c[0]==='toggleGender').length,0,'same gender: no toggle');
 press(t,'Back');press(t,'Female');same(t.calls.filter(c=>c[0]==='toggleGender'),[['toggleGender']]);assert.strictEqual(t.w.gender,FEMALE);checks++;}
{const t=started();press(t,'Keep this name');press(t,'Next');press(t,'Adult (now)');press(t,'Male (now)');
 assert.strictEqual(last(t).title,'Step 4: Traits');assert(last(t).promptText.includes('can have 3. Chosen: Cheerful.'));
 same(labels(t),['Add a trait','Remove a trait','Next: aspiration','Back']);
 press(t,'Add a trait');same(labels(t),['Emotional','Hobby','Back']);press(t,'Emotional');
 same(labels(t),['Hot-Headed','Back'],'chosen, clashing and non-personality traits are left out');press(t,'Hot-Headed');
 assert(last(t).promptText.includes('Chosen: Cheerful, Hot-Headed.'));press(t,'Add a trait');press(t,'Hobby');press(t,'Geek');
 same(labels(t),['Remove a trait','Next: aspiration','Back'],'no Add once the limit is reached');
 press(t,'Remove a trait');same(labels(t),['Cheerful','Hot-Headed','Geek','Back']);press(t,'Cheerful');
 same(t.w.traits,['t_hot','t_geek']);same(t.calls.filter(c=>c[0]==='add'||c[0]==='remove'),[['add','t_hot'],['add','t_geek'],['remove','t_cheer']]);checks++;
 same(t.calls.filter(c=>c[0]==='traitsOpen'),[['traitsOpen']],'trait session opened once, as the EA panel does');
 press(t,'Next: aspiration');same(t.calls.filter(c=>/^traits/.test(c[0])).map(c=>c[0]),['traitsOpen','traitsDone'],'and closed on leaving the step');
 assert(t.marks.includes('guide-trait-add-t_hot-now-2'),'trait adds are logged');assert.strictEqual(last(t).title,'Step 5: Aspiration');same(labels(t),['Love','Fortune','Back'],'CAS order');
 press(t,'Love');same(labels(t),['Soulmate','Back'],'hidden unlockables left out');press(t,'Soulmate');
 same(t.calls.filter(c=>c[0]==='aspiration'),[['aspiration','a_love']]);
 assert.strictEqual(last(t).title,'Your Sim');assert.strictEqual(last(t).promptText,'Ann Lee. Traits: Hot-Headed, Geek. Aspiration: Soulmate.');
 same(labels(t),['Done','Change the name','Change age or gender','Change traits','Change aspiration','Voice and walk style (optional)','Back']);
 press(t,'Change traits');assert.strictEqual(last(t).title,'Step 4: Traits');press(t,'Next: aspiration');press(t,'Fortune');press(t,'Fabulously Wealthy');
 press(t,'Done');assert.strictEqual(last(t).title,'Your Sim is ready');same(labels(t),['Find a home','Add another Sim','Change how my Sims look first','Back']);
 press(t,'Change how my Sims look first');assert.strictEqual(t.tm.mA11yGuideState,'done');checks++;}
// Home: save the household, season, world, home, furnishing, purchase.
function atReady(over){const t=started(over);press(t,'Keep this name');press(t,'Next');press(t,labels(t).find(l=>l.endsWith('(now)')));press(t,'Male (now)');
 press(t,'Next: aspiration');press(t,'Love');press(t,'Soulmate');press(t,'Done');return t;}
{const t=atReady();press(t,'Find a home');assert.strictEqual(last(t).title,'Your household');assert(last(t).promptText.startsWith('Your household is called the Lee household.'));
 same(labels(t),['Save and find a home','Back']);press(t,'Save and find a home');same(t.calls.filter(c=>c[0]==='tray'),[['tray','Lee']]);
 assert(t.ui.some(u=>u[0]==='CASHideCustomizer'),'CAS panels hidden as EA does');assert(t.listeners.ExchangeItemSaved,'waits for the library save');
 t.listeners.ExchangeItemSaved({itemId:'5'});same(t.calls.filter(c=>c[0]==='enter'),[['enter','Lee']]);
 same(t.ui.find(u=>u[0]==='ShowTransitionScreen'),['ShowTransitionScreen',{mode:31}]);assert(t.marks.includes('guide-home-enter-saved'));
 t.w.cas=false;t.w.season=true;t.tick();t.tick(1100);assert.strictEqual(last(t).title,'Choose a season');
 same(labels(t),['Spring','Summer','Fall','Winter']);press(t,'Spring');same(t.calls.filter(c=>c[0]==='season'),[['season','btnSpring',true]]);
 const before=t.shown.length;t.w.season=false;t.tick();assert.strictEqual(t.shown.length,before,'waits for the world map');t.w.worldUp=true;t.tick();t.tick(1600);
 assert.strictEqual(last(t).title,'Choose a world');assert(last(t).promptText.startsWith('Your household has 20,000 simoleons.'));
 same(labels(t),['Willow Creek: 1 house you can afford, 1 empty lot','Oasis Springs: no homes for sale','Back'],'one entry per world, no vacation or hidden worlds');checks++;
 press(t,'Willow Creek: 1 house you can afford, 1 empty lot');const go=t.ui.find(u=>u[0]==='TransitionToNeighborhoodMap');assert.strictEqual(go[1],t.nhds.n1);
 t.tick(600);assert.strictEqual(last(t).title,'Choose a world','waits for the map');t.listeners.NhdMapLoaded();t.tick(1600);
 assert.strictEqual(last(t).title,'Choose a home');
 same(labels(t),['Garden Essence, Pinecrest. 2 bedrooms, 1 bathrooms, furnished 20,000 simoleons',
  'Big Villa, Pinecrest. 4 bedrooms, 3 bathrooms, furnished 85,000 simoleons. Too expensive','Empty Plot, Oakenstead. Empty lot with no house, you build it yourself, 4,000 simoleons','Back'],'houses first, cheapest first, empty lots last');
 press(t,'Big Villa, Pinecrest. 4 bedrooms, 3 bathrooms, furnished 85,000 simoleons. Too expensive');press(t,'Unfurnished: 65,000 simoleons, leaving minus 45,000 simoleons');
 assert.strictEqual(last(t).title,'Not enough money');press(t,'OK');press(t,'Back');
 press(t,'Garden Essence, Pinecrest. 2 bedrooms, 1 bathrooms, furnished 20,000 simoleons');
 same(labels(t),['Furnished: 20,000 simoleons, leaving 0 simoleons','Unfurnished: 17,000 simoleons, leaving 3,000 simoleons','Back']);
 press(t,'Furnished: 20,000 simoleons, leaving 0 simoleons');same(t.ui.find(u=>u[0]==='ConfirmModeOp'),['ConfirmModeOp',{lotData:t.nhds.n1.lots[0]}]);
 t.w.move=true;t.tick(900);same(t.calls.filter(c=>c[0]==='furnish'||c[0]==='dropdownEvent'),[['furnish',1],['dropdownEvent','itemSelected',1]]);
 same(t.clicks,['okay'],'Purchase pressed');assert.strictEqual(t.tm.mA11yGuidePhase,'moved');
 t.w.move=false;t.tick(26000);assert.strictEqual(last(t).title,'Your home is ready','Play offered if the lot does not load');press(t,'Play');
 same(t.calls.filter(c=>c[0]==='play'),[['play','h1','z1']]);t.w.worldUp=false;t.tick();assert.strictEqual(t.tm.mA11yGuidePhase,'');assert(t.marks.includes('guide-home-playing'));checks++;}
{const t=atReady({age:4});press(t,'Find a home');assert.strictEqual(last(t).title,'A grown-up is needed');press(t,'Change age');assert.strictEqual(last(t).title,'Step 2: Age');
 const r=atReady({rude:true});press(r,'Find a home');assert.strictEqual(last(r).title,'Choose another name');
 const s=atReady();press(s,'Find a home');press(s,'Save and find a home');s.tick(16000);assert(s.marks.includes('guide-home-enter-unsaved'),'save timeout still enters the game');
 const c=atReady();press(c,'Find a home');press(c,'Save and find a home');c.listeners.ExchangeItemSaved({itemId:'5'});c.w.cas=false;c.w.worldUp=true;c.tick();c.tick(1600);
 press(c,labels(c)[0]);c.listeners.NhdMapLoaded();c.tick(1600);press(c,labels(c)[0]);c.movePanel.btnOkay.enabled=false;press(c,labels(c)[0]);c.w.move=true;c.tick(900);
 assert.strictEqual(last(c).title,'This home cannot be bought');same(c.clicks,['close'],'move-in window closed, not bought');press(c,'Choose another home');
 assert.strictEqual(last(c).title,'Choose a home');checks++;}
{const t=world();t.tick();t.tick(1100);const intro=last(t);intro.cancellationAction.fn(intro.cancellationAction.params);
 assert.strictEqual(t.tm.mA11yGuideState,'done','Escape on the welcome skips the guide');
 const s=started();const old=s.shown[0].data.actions[0];old.fn(old.params);assert.strictEqual(s.shown.length,2,'a stale dialog answer is ignored');
 const c=started();press(c,'Keep this name');press(c,'Next');const age=last(c);age.cancellationAction.fn(age.cancellationAction.params);
 assert(last(c).title.startsWith('Name:'),'Escape in a list goes back');checks++;}
{const t=started();t.tm.A11yGuideNameDialog=()=>{throw new Error('boom');};press(t,'Back');press(t,'Start');assert.strictEqual(t.tm.mA11yGuideState,'done');
 assert(t.marks.includes('guide-error-boom')&&t.said.some(x=>x.includes('The guide ran into a problem')),'errors close the guide out loud');checks++;}
// Household: add a Sim, name it, relationships, switch back.
{const t=atReady();press(t,'Add another Sim');same(t.calls.find(x=>x[0]==='addSim'),['addSim',6,1,1,1],'a human from scratch, as AddSimMenu does');
 t.tick(600);assert.strictEqual(last(t).title,'Step 1: Name','the new Sim is named first');assert(last(t).promptText.includes('Bo Lee'));
 press(t,'Keep this name');press(t,'Next');press(t,'Adult (now)');press(t,'Female (now)');press(t,'Next: aspiration');press(t,'Love');press(t,'Soulmate');press(t,'Done');
 assert.strictEqual(last(t).title,'Relationships for Bo Lee','a new Sim sets relationships next');same(labels(t),['Ann Lee: No relation','Back']);
 press(t,'Ann Lee: No relation');same(labels(t),['No relation (now)','Parent','Sibling','Spouse','Back']);press(t,'Spouse');
 same(t.calls.filter(x=>x[0]==='rel'),[['rel','79','77',9]]);same(t.calls.filter(x=>x[0]==='trope').map(x=>x[1]),['0','1'],'tropes cleared as RelationshipsPane does');
 same(labels(t),['Ann Lee: Spouse','Back']);press(t,'Back');
 assert.strictEqual(last(t).title,'Your household is ready');assert(last(t).promptText.startsWith('Your household: Bo Lee, Ann Lee.'));
 same(labels(t),['Find a home','Add another Sim','Set relationships','Change another Sim','Change how my Sims look first','Back']);
 press(t,'Change another Sim');same(labels(t),['Ann Lee','Back']);press(t,'Ann Lee');same(t.calls.filter(x=>x[0]==='select'),[['select',0]]);
 assert.strictEqual(last(t).title,'Your Sim');assert(last(t).promptText.startsWith('Ann Lee.'));checks++;}
{const t=atReady({age:4});t.w.slowAdd=true;press(t,'Find a home');assert.strictEqual(last(t).title,'A grown-up is needed');press(t,'Back');
 press(t,'Add another Sim');const n=t.shown.length;t.tick(600);t.tick(600);assert.strictEqual(t.shown.length,n,'waits for CAS to switch to the new Sim');
 t.w.cur=t.w.pending;t.tick(600);assert.strictEqual(last(t).title,'Step 1: Name');press(t,'Keep this name');press(t,'Next');press(t,'Adult (now)');
 press(t,'Female (now)');press(t,'Next: aspiration');press(t,'Love');press(t,'Soulmate');press(t,'Done');press(t,'Back');
 press(t,'Find a home');assert.strictEqual(last(t).title,'Your household','an adult anywhere in the household is enough');checks++;}
// Fresh lot data: the cached world can lack house prices.
{const t=atReady();t.w.fresh={z5:{housePrice:30000,furnishingsPrice:5000,numBeds:3,numBaths:2}};t.w.funds=50000;press(t,'Find a home');press(t,'Save and find a home');
 t.listeners.ExchangeItemSaved({itemId:'5'});t.w.cas=false;t.w.worldUp=true;t.tick();t.tick(1600);press(t,labels(t)[0]);t.listeners.NhdMapLoaded();t.tick(1600);
 assert(labels(t).includes('Empty Plot, Oakenstead. 3 bedrooms, 2 bathrooms, furnished 39,000 simoleons'),'refreshed lot is a furnished house');
 assert(t.nhds.n2.lots[0].updated,'the lot object itself is updated for the move-in panel');
 press(t,'Empty Plot, Oakenstead. 3 bedrooms, 2 bathrooms, furnished 39,000 simoleons');assert.strictEqual(labels(t)[0],'Furnished: 39,000 simoleons, leaving 11,000 simoleons');
 const asked=t.calls.filter(x=>x[0]==='lotData').length;press(t,'Back');press(t,'Back');press(t,labels(t)[0]);
 assert.strictEqual(t.calls.filter(x=>x[0]==='lotData').length,asked,'each lot is refreshed once');checks++;}
// Optional voice and walk style, from the summary.
{const t=atReady();press(t,'Back');assert.strictEqual(last(t).title,'Your Sim');press(t,'Voice and walk style (optional)');
 assert.strictEqual(last(t).title,'Voice and walk style');same(labels(t),['Voice: Sweet','Voice pitch','Walk style: Default','Back']);
 press(t,'Voice: Sweet');same(labels(t),['Sweet (now)','Melodic','Lilted','Back']);same(t.calls.find(x=>x[0]==='voices'),['voices',1,ADULT]);
 press(t,'Melodic');same(t.calls.filter(x=>x[0]==='voice'),[['voice',1]],'0-based voice index, as the voice buttons send');
 same(labels(t),['Sweet','Melodic (now)','Lilted','Back'],'stays open to try others');press(t,'Back');
 press(t,'Voice pitch');same(labels(t),['Lowest','Lower','Middle (now)','Higher','Highest','Back']);press(t,'Highest');
 same(t.calls.filter(x=>x[0]==='pitch'),[['pitch',2,true]],'top of the Melodic range, as a finished slider drag');same(labels(t),['Lowest','Lower','Middle','Higher','Highest (now)','Back']);press(t,'Back');
 press(t,'Walk style: Default');same(labels(t),['Default (now)','Swagger','Back']);press(t,'Swagger');same(t.calls.filter(x=>x[0]==='walk'),[['walk','w2']]);
 press(t,'Back');same(labels(t),['Voice: Melodic','Voice pitch','Walk style: Swagger','Back']);press(t,'Back');assert.strictEqual(last(t).title,'Your Sim','Back returns to the summary');
 press(t,'Done');assert.strictEqual(last(t).title,'Your Sim is ready','the extras never block Done');checks++;}
{const t=atReady({age:4});press(t,'Back');press(t,'Voice and walk style (optional)');same(labels(t),['Voice: Sweet','Voice pitch','Walk style: not for children','Back']);
 press(t,'Walk style: not for children');same(labels(t),['Back']);press(t,'Back');assert.strictEqual(last(t).title,'Voice and walk style');checks++;}
{const t=world();t.tick();t.tick(1100);t.w.cas=false;t.tick();assert.strictEqual(t.tm.mA11yGuideState,'','leaving CAS resets the guide');checks++;}
assert(/this\.A11yGuideFrame\(\);\r?\n\s*try\r?\n\s*\{\r?\n\s*var hudMode:int = this\.A11yWorldHudMode\(\);/.test(source),'checked every frame');checks++;
const added=source.slice(source.indexOf('// BEGIN A11Y GUIDED NEW GAME'),source.indexOf('// END A11Y GUIDED NEW GAME'));
assert(!/\+\+|--/.test(added),'no increment operators');
assert(!/MessageListener\([^)]*,this\)/.test(added),'listeners by name: TooltipManager is not a DisplayObject (live 2026-10-13, Error #1034)');assert(!/CASCustomizer|TextDialogInput/.test(added),'no CASCustomizer, no dialog text boxes');checks++;
console.log(checks+' guided new game checks passed');
