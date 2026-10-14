'use strict';
// Enter on an inventory item: TooltipManager.A11yInventoryMenu posts the
// item's object id (a11y.invitem_enc) only for SimInfoInventoryPanel cells
// outside multiselect, and A11yInvItemActions replays EA's click on the
// remembered cell. Anything unexpected falls back to EA's own click.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const tm=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
function method(name){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(tm);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(tm[at]==='{')depth++;if(tm[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(\*|\w+)/g,'$1');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(tm.slice(start,at-1))+'})',
   {getQualifiedClassName:o=>o.kind||'Widget',encodeURIComponent,String,Object,MouseEvent:{MOUSE_DOWN:'down',MOUSE_UP:'up',CLICK:'click'}});
}
let checks=0;
function fixture(opts){
 const posts=[],events=[];
 const panel={btnMultiselect:'multi' in opts?opts.multi:{Selected:false}};
 const cell={kind:opts.kind||'widgets.Gameplay.SimInfoHUD.InventoryPanel::InventoryCellViewButton',stage:{},
   GetObjectId:()=>{if(opts.throws)throw new Error('x');return 'id' in opts?opts.id:'12345';}};
 const ctx={mA11yInvCell:null,mA11yActivating:false,
   A11yLoadedWidget:n=>n==='SimInfoInventoryPanel'&&!opts.noPanel?panel:null,
   A11yIsInside:(o,root)=>root===panel&&!opts.outside,A11yIsLive:o=>!!o&&!opts.dead,
   A11yPostToPython:(c,p)=>posts.push([c,p]),A11ySafeDispatch:(o,e)=>events.push([o===cell,e])};
 ctx.A11yInventoryMenu=method('A11yInventoryMenu');ctx.A11yInvItemActions=method('A11yInvItemActions');
 return {ctx,cell,posts,events};
}
// Intercepted: an ordinary Sim inventory item.
{const f=fixture({});assert.strictEqual(f.ctx.A11yInventoryMenu(f.cell),true);
 assert.deepStrictEqual(f.posts,[['a11y.invitem_enc','12345']]);assert.strictEqual(f.ctx.mA11yInvCell,f.cell);checks++;
 f.ctx.A11yInvItemActions();
 assert.deepStrictEqual(f.events,[[true,'down'],[true,'up'],[true,'click']]);
 assert.strictEqual(f.ctx.mA11yInvCell,null);assert.strictEqual(f.ctx.mA11yActivating,false);checks++;
 f.events.length=0;f.ctx.A11yInvItemActions();assert.deepStrictEqual(f.events,[]);checks++;}   // replay only once
// EA's click stays: other controls, other panels, multiselect, bad ids.
for(const [label,opts] of [
 ['another control',{kind:'olympus.controls::Button'}],
 ['no inventory panel',{noPanel:true}],
 ['outside the panel',{outside:true}],
 ['multiselect on',{multi:{Selected:true}}],
 ['multiselect unknown',{multi:{}}],
 ['no multiselect button',{multi:null}],
 ['empty id',{id:''}],['zero id',{id:'0'}],['null id',{id:null}],
 ['id lookup throws',{throws:true}]]){
 const f=fixture(opts);assert.strictEqual(f.ctx.A11yInventoryMenu(f.cell),false,label);
 assert.deepStrictEqual(f.posts,[],label);assert.strictEqual(f.ctx.mA11yInvCell,null,label);checks++;
}
// A cell that left the stage is not clicked.
{const f=fixture({dead:true});f.ctx.mA11yInvCell=f.cell;f.ctx.A11yInvItemActions();assert.deepStrictEqual(f.events,[]);checks++;}
// Wired into Enter after the purchase footer, registered, and int-gate safe.
assert(/A11yPickerFooter\(_loc2_\)\) \{ return; \}\s*\n\s*if\(confirm && this\.A11yInventoryMenu\(_loc2_\)\) \{ return; \}/.test(tm));checks++;
assert(/AddMessageListenerByName\("A11yInvItemActions",this\.A11yInvItemActions,"A11yNarrator"\)/.test(tm));checks++;
const added=tm.slice(tm.indexOf('public function A11yInventoryMenu'),tm.indexOf('public function A11yWants'));
assert(!/\+\+|--/.test(added),'no increment operators');assert(!/InventoryCellViewButton\s*\)|as InventoryCellViewButton|:InventoryCellViewButton/.test(added),'no class reference');checks++;
console.log(checks+' inventory sell template checks passed');
