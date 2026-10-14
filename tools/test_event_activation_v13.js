'use strict';
// v13 event planner / HUD activation fixtures against the actual shared template bodies.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function body(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig,'missing '+name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 return {params:sig[1],text:source.slice(start,at-1)};
}
function method(name){
 const b=body(name);
 const strip=s=>s.replace(/:\s*(DisplayObject|TextField|String|Object|Boolean|Error|int)\b/g,'').replace(/\s+as\s+(DisplayObject|TextField)\b/g,'');
 return vm.runInNewContext('(function('+strip(b.params)+'){'+strip(b.text)+'})',{getQualifiedClassName:o=>o.kind||'',MouseEvent:{MOUSE_DOWN:'mouseDown',MOUSE_UP:'mouseUp',CLICK:'click'}});
}
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}
const proxy=method('A11yActionProxy');

test('Planner role slot resolves to its mcPickSims button',()=>{
 const cell={kind:'widgets.Gameplay.SituationCreation.controls::RoleSlotCellView',mcPickSims:{kind:'PushButton'}};
 assert.strictEqual(proxy(cell),cell.mcPickSims);
});
test('mcPickSims on any other class is not treated as a role slot',()=>{
 const other={kind:'widgets.Other::Cell',mcPickSims:{}};
 assert.strictEqual(proxy(other),other);
});
test('Calendar Add row still resolves to btnAdd (regression)',()=>{
 const row={kind:'widgets.Gameplay.Calendar.controls::ScheduleAdd',btnAdd:{},txtLabel:{}};
 assert.strictEqual(proxy(row),row.btnAdd);
});
test('Plain controls resolve to themselves',()=>{
 const plain={kind:'olympus.controls::PushButton'};
 assert.strictEqual(proxy(plain),plain);
});
test('Activation speaks the unavailable token when the proxy click is refused',()=>{
 const activate=body('A11yActivate').text;
 const branch=activate.indexOf('if(this.A11yActionProxy(_loc2_) != _loc2_)');
 assert(branch>=0,'proxy branch present');
 const window=activate.slice(branch,branch+600);
 assert(/if\(!this\.A11yClickControl\(this\.A11yActionProxy\(_loc2_\)\)\)\s*\{\s*this\.A11yPostToPython\("a11y\.widget_enc",encodeURIComponent\("0\|0\|action unavailable"\)\);\s*\}/.test(window),'refused click is announced');
 assert(/return;/.test(window),'branch still returns');
});
test('Disabled proxy targets are still refused by A11yClickControl',()=>{
 const click=method('A11yClickControl');
 const ui={A11yIsLive:()=>true,A11ySafeDispatch:()=>{},mA11yActivating:false};
 assert.strictEqual(click.call(ui,{enabled:false}),false);
 assert.strictEqual(click.call(ui,{mouseEnabled:false}),false);
 assert.strictEqual(click.call(ui,{enabled:true}),true);
});
test('A text-less PhoneButton is announced with the phone token, after the map label',()=>{
 const announce=body('A11yAnnounceDisplay').text;
 const map=announce.indexOf('_loc7_ = this.A11yMapLabel(param1);');
 const phone=announce.indexOf('if(_loc2_.length == 0 && getQualifiedClassName(param1).indexOf("PhoneButton") >= 0) { _loc2_ = ["0|0|phone"]; }');
 assert(map>=0&&phone>map,'phone token line follows the map label line');
});
test('Narrator translates both new tokens',()=>{
 const py=fs.readFileSync(path.join(__dirname,'../Scripts/tyjokr_a11y_narrator.py'),'utf8');
 assert(/seg in \('checked', 'unchecked', 'increase', 'decrease', 'phone', 'action unavailable'\)/.test(py));
});

const toggleCell=method('A11yPickerToggleCell');
function pickerUi(rootKind,layoutKind='olympus.layout::SelectableRecyclingGridLayout'){return {mA11yActiveModalRoot:{kind:rootKind,stage:{}},A11yIsLive:item=>!!item&&item.visible!==false,A11yFindScrollList:()=>({}),A11yGridLayout:()=>layoutKind?{kind:layoutKind}:null};}
test('Native companion cards announce selection only with their visible Done button',()=>{
 const ui=pickerUi('widgets.Pickers::PickersMain');
 const owner={kind:'widgets.Pickers.controls.SimPicker::SimPicker',btnDone:{visible:true}};
 const row={kind:'widgets.Pickers.controls.SimPicker::DefaultSimPickerCellView',Selected:false,parent:owner};
 assert.strictEqual(toggleCell.call(ui,row),true);
 owner.btnDone.visible=false;
 assert.strictEqual(toggleCell.call(ui,row),false);
 owner.btnDone.visible=true;
 owner.kind='widgets.Other::Picker';
 assert.strictEqual(toggleCell.call(ui,row),false);
});
test('Autoaccept travel rows do not announce a checkbox state',()=>{
 const row={kind:'widgets.Pickers.controls.PickerCells::ObjectPickerIconTextCellView',Selected:false};
 for(const layout of ['olympus.layout::RecyclingGridLayout','olympus.layout::GridLayout',null]) {
  assert.strictEqual(toggleCell.call(pickerUi('widgets.Pickers::PickersMain',layout),row),false);
 }
});
test('Event Sim selections expose checked state while hire quantity rows do not',()=>{
 const ui=pickerUi('widgets.Pickers::PickersMain');
 const owner={kind:'widgets.Pickers.controls.SimPicker::SimPicker',btnDone:{visible:true}};
 const row={kind:'widgets.Pickers.controls.SimPicker::SituationSimPickerCellView',Selected:true,parent:owner,mcHireSimControl:{visible:false}};
 assert.equal(toggleCell.call(ui,row),true);
 row.mcHireSimControl.visible=true;assert.equal(toggleCell.call(ui,row),false);
});
test('Object picker rows inside PickersMain are toggle cells',()=>{
 const ui=pickerUi('widgets.Pickers::PickersMain');
 const row={kind:'widgets.Pickers.controls.PickerCells::ObjectPickerIconTextRelCellView',Selected:false};
 assert.strictEqual(toggleCell.call(ui,row),true);
});
test('Purchase rows, non-picker owners and cells without Selected are not toggle cells',()=>{
 const ui=pickerUi('widgets.Pickers::PickersMain');
 assert.strictEqual(toggleCell.call(ui,{kind:'widgets.Pickers.controls::PurchasePickerCellView',Selected:false}),false);
 assert.strictEqual(toggleCell.call(ui,{kind:'widgets.Pickers.controls.PickerCells::ObjectPickerCellView'}),false);
 assert.strictEqual(toggleCell.call(pickerUi('widgets.Gameplay.Calendar::CalendarMain'),{kind:'widgets.Pickers.controls.PickerCells::ObjectPickerCellView',Selected:true}),false);
});
test('Checkbox state reads Selected on toggle cells before the Checkbox class path',()=>{
 const state=body('A11yCheckboxState').text;
 const branch=state.indexOf('if(this.A11yPickerToggleCell(param1))');
 const checkbox=state.indexOf('if(_loc2_.indexOf("Checkbox") >= 0)');
 assert(branch>=0&&checkbox>branch,'toggle-cell branch precedes the Checkbox branch');
 assert(/return Object\(param1\)\["Selected"\] == true \? "checked" : "unchecked";/.test(state.slice(branch,branch+300)));
});
test('Activation schedules the settled reread for a toggled picker row',()=>{
 const activate=body('A11yActivate').text;
 const click=activate.indexOf('this.A11ySafeDispatch(_loc2_,MouseEvent.CLICK);');
 const after=activate.slice(click,click+500);
 assert(/if\(this\.A11yPickerToggleCell\(_loc2_\)\)\s*\{\s*this\.mA11yFocusPending = _loc2_;\s*this\.mA11yFocusDue = getTimer\(\) \+ 150;\s*\}/.test(after),'settled reread scheduled after the click');
});
const detailBody=body('A11yChoiceDescription');
const detailKeys=new Proxy({}, {get:(_,key)=>({toString:(...args)=>key+': '+args.join(', ')})});
class PlainField {set htmlText(s){this.text=s.replace(/<br\s*\/>/gi,'\n').replace(/<[^>]+>/g,'');}}
const details=vm.runInNewContext('(function(item){'+detailBody.text.replace(/:\s*(DisplayObject|TextField|String|Object|Boolean|Error|int|Array)\b/g,'')+'})',{
 getQualifiedClassName:o=>o.kind||'', int:Number, TextField:PlainField,
 getDefinitionByName:name=>name.endsWith('KeysGP')?detailKeys:name.endsWith('TraitsStaticData')?{GetStaticData:id=>id==='missing'?null:{GetTraitOriginDescriptionLocKeyBySimIdToken:tokens=>{assert.equal(tokens.simId,'123');return {toString:()=>id};}}}:{PANEL_TYPE_AGENT_BASED_CAREER:4,CATEGORY_WORK_FROM_HOME:5,PANEL_TYPE_FREELANCE_CAREER:6}
});
const eventRow={kind:'widgets.Gameplay.SituationCreation.controls::SituationCellView'};
function detailUi(data){return {A11yFindScrollList:()=>({}),A11yGridLayout:()=>({GetCellIndexToDataIndex:i=>{assert.equal(i,2);return 7;},GetDataAtIndex:i=>{assert.equal(i,7);return data;}}),A11yCellIndexOf:()=>2};}
function eventData(scoring=true){return {isScoring:scoring,icon_info:{GetDesc:()=>'<b>Keg description</b>',GetMainObjective:()=>'Drink together',GetLocationDesc:()=> 'Residential only'},challenge_reward_override:[],rewards:[{display_name:['Bronze']},{display_name:['Gold']}]};}
test('Focused event reads its own description, challenge and location through mapped row data',()=>{
 const value=details.call(detailUi(eventData()),eventRow);
 assert(value.includes('Keg description'));assert(value.includes('Drink together'));assert(value.includes('Residential only'));assert(value.includes('Gold'));assert(!value.includes('Bronze'));assert(!value.includes('<b>'));
});
test('Unscored event omits challenge and rewards but retains description and restriction',()=>{
 const value=details.call(detailUi(eventData(false)),{kind:'TextField',parent:eventRow});
 assert(value.includes('Keg description'));assert(value.includes('Residential only'));assert(!value.includes('Drink together'));assert(!value.includes('Gold'));
});
test('Event challenge override takes precedence over rewards',()=>{
 const data=eventData();data.challenge_reward_override=['Special reward'];
 const value=details.call(detailUi(data),eventRow);assert(value.includes('Special reward'));assert(!value.includes('Gold'));
});
test('Unrelated and stale rows do not read selected panel content',()=>{
 assert.equal(details.call(detailUi(eventData()),{kind:'Other'}),'');
 const ui=detailUi(eventData());ui.A11yCellIndexOf=()=>-1;assert.equal(details.call(ui,eventRow),'');
 assert(!/SelectionData|SelectCell|dispatchEvent|txtSituationDesc/.test(detailBody.text));
});
test('Career description gets the selected Sim token and native benefit precedence',()=>{
 const data={sim_id:'123',description:{toString:tokens=>{assert.equal(tokens.simId,'123');return 'Career description';}},IsAgentRequired:()=>false,benefit_description:{IsValid:()=>true,toString:()=> 'Benefits'},work_from_home_description:{IsValid:()=>true,toString:()=> 'Hidden WFH'},career_category:5,trackStaticData:{branchesData:[]}};
 const value=details.call(detailUi(data),{kind:'widgets.Gameplay.CareerSelector::TrackBlock'});
 assert(value.includes('Career description'));assert(value.includes('Benefits'));assert(!value.includes('Hidden WFH'));
});
test('Scrolled recycled career index is not converted a second time',()=>{
 const row={kind:'widgets.Gameplay.CareerSelector::TrackBlock'};
 const data={sim_id:'123',description:{toString:()=> 'Scrolled career explanation'},IsAgentRequired:()=>false,career_panel_type:0,trackStaticData:{branchesData:[]}};
 const layout={kind:'olympus.layout::SelectableRecyclingGridLayout',GetCellIndexToDataIndex:()=>{throw Error('Already converted by GetGridIndexOfCell');},GetDataAtIndex:index=>{assert.equal(index,17);return data;}};
 const ui={A11yFindScrollList:()=>({}),A11yGridLayout:()=>layout,A11yCellIndexOf:()=>17};
 assert(details.call(ui,row).includes('Scrolled career explanation'));
});
test('Freelancer includes sorted unique trades and tolerates a missing trait',()=>{
 const data={sim_id:'123',description:{toString:()=> 'Freelancer explanation'},IsAgentRequired:()=>false,career_panel_type:6,currentCareerLevel:{agents_available:['Writer','Artist','Writer','missing']},trackStaticData:{branchesData:[]}};
 const value=details.call(detailUi(data),{kind:'widgets.Gameplay.CareerSelector::TrackBlock'});
 assert(value.includes('Freelancer explanation'));assert(value.includes('Artist, Writer'));assert(!value.includes('Writer, Writer'));
});
console.log(count+' event activation checks passed (source bodies, not in-game verification)');
