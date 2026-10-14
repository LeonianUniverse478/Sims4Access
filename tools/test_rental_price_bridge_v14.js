'use strict';
// Execute the production AS method with only native service boundaries stubbed.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
const start=source.indexOf('      public function A11yLotRentalPrice(');
const end=source.indexOf('      public function A11yResolveLoc(',start);
const method=source.slice(start,end).replace('public function','function').replace(/:\s*(String|void|Number|Object|Boolean|Error)\b(?!\s*\()/g,'');
let raw,calculator,calls=[],answers=[];
const context=vm.createContext({Number,String,isFinite,NaN,uint:x=>x>>>0,
 CommunicationManager:{CallGameService:(name,zone)=>{calls.push([name,zone]);if(raw instanceof Error)throw raw;return name==='GetNeighborhoodLotData'?raw:calculator;}}});
const run=vm.runInContext('('+method+')',context);
const owner={A11yPostToPython:(command,payload)=>answers.push([command,payload])};
const zone='948853709175653415';
function price(data,calc={multiply:0.02,add:0}){raw=data;calculator=calc;calls=[];answers=[];run.call(owner,zone,'17');assert.equal(calls[0][1],zone);assert.equal(answers[0][0],'a11y.lotprice_enc');assert.equal(answers[0][1].split('|')[2],'17');return Number(answers[0][1].split('|')[1]);}
const normal={buildingType:0,lotDescriptionData:{price:3000},housePrice:15000,furnishingsPrice:1850};
assert.equal(price(normal),397);
assert.equal(price({...normal,buildingType:1,depositBase:1000}),57);
assert.equal(price(normal,{multiply:0.02,add:0.9}),397);
for(const data of [null,{},new Error('unavailable'),{...normal,furnishingsPrice:Infinity},{...normal,lotDescriptionData:null},{...normal,housePrice:-1}])assert.equal(price(data),0);
for(const calc of [null,{}, {multiply:-1,add:0},{multiply:Infinity,add:0},{multiply:1e20,add:0}])assert.equal(price(normal,calc),0);
calls=[];answers=[];run.call(owner,'948|bad','17');assert.equal(calls.length,0);assert.equal(answers.length,0);
run.call(owner,zone,'17|bad');assert.equal(calls.length,0);assert.equal(answers.length,0);
console.log('16 rental price bridge checks passed');
