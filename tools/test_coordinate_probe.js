'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name,runtime){
 const signature=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);assert(signature,name);
 let start=signature.index+signature[0].length,end=start,depth=1;
 while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
 const strip=s=>s.replace(/:\s*(?:Sprite|Stage|Point|Rectangle|Array|String|Object|Number|Boolean|Error|Event|int)\b/g,'');
 return vm.runInNewContext('(function('+strip(signature[1]) +'){'+strip(source.slice(start,end-1))+'})',runtime);
}
let now=0;
class Point{constructor(x,y){this.x=x;this.y=y;}}
class Sprite{
 constructor(){this.visible=true;this.parent=null;this.listeners=new Map();}
 addEventListener(name,fn){this.listeners.set(name,fn);}
 removeEventListener(name,fn){if(this.listeners.get(name)===fn)this.listeners.delete(name);}
 localToGlobal(){return new Point(this.x,this.y);}
}
function fixture(){
 const services=[],replies=[],stage={stageWidth:2880,stageHeight:1800,scaleMode:'noScale',align:''};
 const layer={stage,children:[],addChild(s){this.children.push(s);s.parent=this;},removeChild(s){this.children.splice(this.children.indexOf(s),1);s.parent=null;}};
 const ui={mTooltipsLayer:layer,mA11yCoordinateMarker:null,mA11yBuildControls:true,mA11yKeyboard:true,mA11yKeyboardLease:10000,
  mA11yBuildCursor:true,mode:2,blocked:false,zone:'954785138800659508',bind:true,
  A11yWorldHudMode(){return this.mode;},A11yBuildBlocked(){return this.blocked;},
  A11yBuildBounds(){return {left:8,top:80,right:2872,bottom:1680};},
  A11yPostToPython(name,text){replies.push([name,decodeURIComponent(text).split('|')]);}};
 const runtime={Point,Sprite,Stage:Object,Event:{ENTER_FRAME:'frame'},Number,String,Math,isFinite,int:Math.trunc,
  getTimer:()=>now,encodeURIComponent,
  getDefinitionByName:()=>({StageWidth:2880,StageHeight:1800}),
  CommunicationManager:{CallGameService(name,data){
   services.push([name,data]);if(name==='BBGetCurrentZoneId')return ui.zone;
   if(name==='BindDisplayObject'&&ui.bind){data.displayObject.x=1440;data.displayObject.y=720;}
  }}};
 for(const name of ['A11yCoordinateCancel','A11yCoordinateReply','A11yCoordinateProbe','A11yCoordinateFrame'])ui[name]=method(name,runtime).bind(ui);
 return {ui,layer,stage,replies,services};
}
function request(f,serial=1,zone=f.ui.zone){f.ui.A11yCoordinateProbe(['A11y','coords',String(serial),'10','3','20','0',zone]);}
let count=0;function test(name,fn){now=0;fn();count++;console.log('PASS '+name);}
test('native read-only projection returns point and both coordinate dimensions',()=>{
 const f=fixture();request(f);f.ui.A11yCoordinateFrame({});
 assert.equal(f.replies[0][0],'a11y.coords_enc');
 assert.deepStrictEqual(Array.from(f.replies[0][1]),['1',f.ui.zone,'point','1440','720','2880','1800','noScale','','2880','1800','8','80','2872','1680']);
 assert.equal(f.layer.children.length,0);assert.equal(f.ui.mA11yCoordinateMarker,null);assert.equal(f.ui.mA11yBuildCursor,true);
});
test('projection uses only zone query, bind and unbind, never input services',()=>{
 const f=fixture();request(f);f.ui.A11yCoordinateFrame({});
 assert(f.services.every(([name])=>['BBGetCurrentZoneId','BindDisplayObject','UnbindDisplayObject'].includes(name)));
});
test('blocked context is refused without a marker or cursor changes',()=>{
 const f=fixture();f.ui.blocked=true;request(f);assert.equal(f.replies[0][1][2],'blocked');assert.equal(f.layer.children.length,0);assert.equal(f.ui.mA11yBuildCursor,true);
});
test('zone mismatch is refused without binding',()=>{
 const f=fixture();request(f,1,'other');assert.equal(f.replies[0][1][2],'zonechanged');assert(!f.services.some(([n])=>n==='BindDisplayObject'));
});
test('mode change cancels an outstanding marker',()=>{
 const f=fixture();request(f);f.ui.mode=1;f.ui.A11yCoordinateFrame({});assert.equal(f.replies[0][1][2],'blocked');assert.equal(f.layer.children.length,0);
});
test('offscreen timeout still supplies viewport measurements and cleans up',()=>{
 const f=fixture();f.ui.bind=false;request(f);now=2000;f.ui.A11yCoordinateFrame({});
 assert.equal(f.replies[0][1][2],'viewport');assert.equal(f.replies[0][1][3],'NaN');assert.equal(f.replies[0][1][5],'2880');assert.equal(f.layer.children.length,0);
});
test('replacement request cancels its own previous marker only',()=>{
 const f=fixture();request(f);request(f,2);assert.equal(f.replies[0][1][2],'cancelled');assert.equal(f.layer.children.length,1);
 f.ui.A11yCoordinateFrame({});assert.equal(f.replies[1][1][0],'2');assert.equal(f.layer.children.length,0);
});
test('invalid coordinates never bind or touch any cursor',()=>{
 const f=fixture();f.ui.A11yCoordinateProbe(['A11y','coords','1','NaN','3','20','0',f.ui.zone]);assert.equal(f.layer.children.length,0);assert.equal(f.services.length,0);
});
test('lease expiry before frame cancels without changing existing cursor',()=>{
 const f=fixture();request(f);now=20000;f.ui.A11yCoordinateFrame({});assert.equal(f.replies[0][1][2],'blocked');assert.equal(f.ui.mA11yBuildCursor,true);
});
test('encoded route adds exactly one probe dispatch',()=>{
 assert(source.includes('if(_loc2_[1] == "coords" && _loc2_.length == 8) { this.A11yCoordinateProbe(_loc2_); return; }'));
 const probe=source.slice(source.indexOf('public function A11yCoordinateCancel'),source.indexOf('public function A11yBuildProjectionFrame'));
 for(const forbidden of ['SetupVirtualCursor','SetVirtualCursorPosition','SendVirtualCursorClick','BBGamepadPlaceMultiple'])assert(!probe.includes(forbidden),forbidden);
});
console.log(count+' coordinate probe checks passed (native renderer mocked).');
