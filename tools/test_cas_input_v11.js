'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(sig);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/:\s*(DisplayObject|TextField|String|Object|Boolean|Error|int)\b/g,'').replace(/\s+as\s+(DisplayObject|TextField)\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1])+'){'+strip(source.slice(start,at-1))+'})',{getQualifiedClassName:o=>o.kind,encodeURIComponent});
}
function fixture(){
 const owner={kind:'widgets.CAS.NameField::CASNameFieldMain'},controls={parent:owner};owner.mcEditModeControls=controls;
 const first={parent:controls,txtDefault:{text:'First Name',visible:false}},last={parent:controls,txtDefault:{text:'Last Name',visible:false}};
 for(const field of [first,last])Object.defineProperty(field,'DefaultText',{get(){throw Error('EA DefaultText is write-only');},set(value){field.txtDefault.text=value;}});
 const input={parent:first,type:'input',text:'',caret:3},lastInput={parent:last,type:'input',text:'Doe',caret:1};
 controls.txtFirstName=first;controls.txtLastName=last;
 const stage={focus:input},calls=[],rings=[],ui={mA11yKeyboard:true,mA11yCASInput:null,mTooltipsLayer:{stage},
  A11yCASInputField:method('A11yCASInputField'),follow:method('A11yFollowCASInput'),
  A11yIsLive:item=>{if(!item)return false;for(let n=item;n;n=n.parent)if(n.visible===false)return false;return true;},
  A11yIsInside:(item,root)=>{for(let n=item;n;n=n.parent)if(n===root)return true;return false;},
  A11yTextValue:item=>item.text,A11yDrawFocusRing:item=>rings.push(item),A11yClearRing:()=>rings.push(null),
  A11yCASNameLabel:item=>item.visible===false?null:item,
  A11yPostToPython:(command,payload)=>calls.push([command,decodeURIComponent(payload)]),
  A11yAnnounceDisplay:item=>calls.push(['fallback',item])};
 return {owner,controls,first,last,input,lastInput,stage,calls,rings,ui};
}
let count=0;function test(name,run){run();count++;console.log('PASS '+name);}
test('Native first-name focus announces localized label without moving caret',()=>{const f=fixture();f.first.DefaultText='Prénom';f.ui.follow();assert.deepStrictEqual(f.calls,[['a11y.focus_enc','0|0|Prénom']]);assert.strictEqual(f.stage.focus,f.input);assert.strictEqual(f.input.caret,3);assert.strictEqual(f.ui.mA11yFocused,f.first);});
test('Native Tab to last name announces label and existing value once',()=>{const f=fixture();f.ui.follow();f.stage.focus=f.lastInput;f.ui.follow();assert.deepStrictEqual(f.calls[1],['a11y.focus_enc','0|0|Last Name. Doe']);f.lastInput.text='Does';f.ui.follow();assert.strictEqual(f.calls.length,2);assert.strictEqual(f.lastInput.caret,1);});
test('Leaving and reopening the same field reannounces it',()=>{const f=fixture();f.ui.follow();f.stage.focus=null;f.ui.follow();f.stage.focus=f.input;f.ui.follow();assert.strictEqual(f.calls.length,2);});
test('Hidden CAS editor and unrelated name controls are excluded',()=>{const f=fixture();f.controls.visible=false;f.ui.follow();assert.strictEqual(f.calls.length,0);f.controls.visible=true;f.owner.kind='unrelated::CASNameFieldMain';f.ui.follow();assert.strictEqual(f.calls.length,0);});
test('Only native first and last fields are followed',()=>{const f=fixture();f.stage.focus={parent:f.controls,type:'input',text:'Other'};f.ui.follow();assert.strictEqual(f.calls.length,0);});
test('Keyboard off and static text retain native behavior without added narration',()=>{const f=fixture();f.ui.mA11yKeyboard=false;f.ui.follow();assert.strictEqual(f.calls.length,0);f.ui.mA11yKeyboard=true;f.input.type='dynamic';f.ui.follow();assert.strictEqual(f.calls.length,0);assert.strictEqual(f.stage.focus,f.input);});
test('Placeholder is not duplicated as field value',()=>{const f=fixture();f.input.text='First Name';f.ui.follow();assert.deepStrictEqual(f.calls,[['a11y.focus_enc','0|0|First Name']]);});
test('Missing field and unloading owner fail closed',()=>{const f=fixture();f.controls.txtFirstName=null;f.ui.follow();assert.strictEqual(f.calls.length,0);Object.defineProperty(f.owner,'mcEditModeControls',{get(){throw Error('unload');}});assert.doesNotThrow(()=>f.ui.follow());});
test('Closing the editor clears its ring and resumes at the visible name label',()=>{const f=fixture();f.owner.txtFullNameDisplay={visible:true};f.ui.follow();f.stage.focus=null;f.ui.follow();assert.strictEqual(f.rings.at(-1),null);assert.strictEqual(f.ui.mA11yFocused,f.owner.txtFullNameDisplay);assert.strictEqual(f.stage.focus,null);});
test('An unrelated new focus owner is not cleared on name editor exit',()=>{const f=fixture();f.ui.follow();const dialog={};f.ui.mA11yFocused=dialog;f.stage.focus=null;f.ui.follow();assert.strictEqual(f.ui.mA11yFocused,dialog);assert.strictEqual(f.rings.length,1);});
console.log(count+' CAS native input checks passed');
