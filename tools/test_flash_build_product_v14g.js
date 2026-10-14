/* Execute the proposed AS3 product-preservation bodies (v3) against message fixtures.
 * Reads build/claude-proposals/a11y-build-product-preserve.as until Codex
 * integrates it into TooltipManager_patched.as (then the production template
 * is used automatically once the proposal file is removed).
 * Strips types only. Verifies decisions, not native rendering.
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const PROPOSAL = path.join(__dirname, '../build/claude-proposals/a11y-build-product-preserve.as');
const SOURCE = path.join(__dirname, '../flash/TooltipManager_patched.as');
const source = fs.readFileSync(SOURCE, 'utf8');
let now = 10000;
const runtime = {
  int: Math.trunc, Boolean, getTimer: () => now,
  getQualifiedClassName: obj => (obj && obj.__class) || 'Object',
};
{
  const m = /A11Y_PRODUCT_RESTORE_WINDOW:int = (\d+);/.exec(source);
  assert(m, 'window constant');
  runtime.A11Y_PRODUCT_RESTORE_WINDOW = Number(m[1]);
}
assert(!/ORDER_SLACK/.test(source), 'no wall-clock slack in v3');

function method(name) {
  const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
  assert(signature, 'Missing ' + name);
  let start = signature.index + signature[0].length, i = start, depth = 1;
  while (depth && i < source.length) {
    if (source[i] === '{') depth++;
    if (source[i] === '}') depth--;
    i++;
  }
  assert.equal(depth, 0, name + ' braces');
  const types = /:\s*(?:DisplayObject|Boolean|Number|String|Object|Array|Rectangle|Sprite|Point|int|Error|Class|Event)\b/g;
  const body = source.slice(start, i - 1).replace(types, '').replace(/\s+as\s+Class\b/g, '');
  return vm.runInNewContext('(function(' + signature[1].replace(types, '') + ') {' + body + '})', runtime, {filename: name});
}

const METHODS = ['A11yBuildProductObserve', 'A11yBuildProductOrdinary', 'A11yBuildProductSelected',
                 'A11yBuildProductModal', 'A11yBuildProductDropped', 'A11yBuildProductFrame',
                 'A11yBuildProductForget', 'A11yBuildProductRestore'];

function fixture() {
  now = 10000;
  const listeners = {}, selects = [], posts = [];
  const ctx = {
    mA11yBuildControls: true,
    mA11yBuildProduct: null, mA11yBuildProductLost: false, mA11yBuildProductModals: 0,
    mA11yBuildProductClosedAt: 0, mA11yBuildProductDropPending: false, mA11yBuildProductObserved: false,
    mA11yBuildCursor: false, mA11yBuildPositionKnown: false, mA11yKeyboard: true, blocked: false,
    A11yBuildBlocked() { return this.blocked; },
    A11yPostToPython(command,payload) { posts.push([command,payload]); },
    A11yBuildLog() {}, A11yEditing() { return false; },
  };
  runtime.CommunicationManager = {AddMessageListenerByName: (name, fn) => { listeners[name] = fn; }};
  for (const name of METHODS) ctx[name] = method(name);
  const product = (extra) => Object.assign({
    __class: 'gamedata.BuildBuy.shared::CatalogProduct',
    resourceKey: {type: 1, group: 2, instance: 3}, sculptType: 0, pondType: 0, stateIndex: 0,
    Select(...args) { selects.push({product: this, args}); },
  }, extra || {});
  const frame = (n = 1) => { for (let i = 0; i < n; i++) { now += 16; ctx.A11yBuildProductFrame(); } };
  // The player's workflow: product held, the accessibility window opens
  // (EA cancels the tool: BBActionModeChanged in the same dispatch, before
  // or after our SetModalVisible listener), frames pass, the window closes,
  // the menu action re-enables the cursor, restore runs before the action.
  const modalRound = (order) => {
    if (order === 'inspector-first') { ctx.A11yBuildProductDropped(0); ctx.A11yBuildProductModal(true); }
    else { ctx.A11yBuildProductModal(true); ctx.A11yBuildProductDropped(0); }
    frame(180);
    ctx.A11yBuildProductModal(false);
    frame(12);
    ctx.mA11yBuildCursor = true;
  };
  return {ctx, listeners, selects, posts, product, frame, modalRound};
}

let checks = 0;
function check(name, fn) { fn(); checks++; console.log('ok - ' + name); }

check('observe registers the four listeners once', () => {
  const f = fixture();
  f.ctx.A11yBuildProductObserve(); f.ctx.A11yBuildProductObserve();
  assert.deepStrictEqual(Object.keys(f.listeners).sort(),
    ['BBActionModeChanged', 'BBProductSelected', 'BBToggleBuildSelect', 'SetModalVisible']);
});

check('positive classifier: CatalogProduct with a key, no sculpt or pond; other classes rejected', () => {
  const f = fixture();
  for (const bad of [f.product({sculptType: 2}), f.product({pondType: 1}), f.product({resourceKey: null}),
                     f.product({__class: 'gamedata.BuildBuy.shared::CatalogRoom'}), null, {}]) {
    f.ctx.A11yBuildProductSelected({product: bad});
    assert.equal(f.ctx.mA11yBuildProduct, null);
  }
  const p = f.product({stateIndex: 2});
  f.ctx.A11yBuildProductSelected({product: p});
  assert.strictEqual(f.ctx.mA11yBuildProduct, p);
});

check('the ordinary workflow restores once with the recorded state index, either listener order', () => {
  for (const order of ['ours-first', 'inspector-first']) {
    const f = fixture();
    f.ctx.A11yBuildProductSelected({product: f.product({stateIndex: 3})});
    f.modalRound(order);
    assert.equal(f.ctx.A11yBuildProductRestore(), true, order);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(f.selects.map(s => s.args))), [[null, null, 0, 2, 3]], order);
    assert.equal(f.ctx.A11yBuildProductRestore(), false, order);   // once
    assert.equal(f.selects.length, 1);
  }
});

check('first activation: no cursor session is needed, keyboard mode is', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.modalRound('ours-first');                                      // cursor was never on before the window
  assert.equal(f.ctx.A11yBuildProductRestore(), true);
  const g = fixture();
  g.ctx.mA11yKeyboard = false;                                     // keyboard mode off: not ours
  g.ctx.A11yBuildProductSelected({product: g.product()});
  g.modalRound('ours-first');
  assert.equal(g.ctx.A11yBuildProductRestore(), false);
  assert.equal(g.selects.length, 0);
});

check('a real Escape one frame before the modal is the player letting go, not a cancellation to claim', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.ctx.A11yBuildProductDropped(null);                             // Escape / Select tool
  f.frame(1);                                                      // a frame passes before the menu opens
  f.ctx.A11yBuildProductModal(true); f.frame(180); f.ctx.A11yBuildProductModal(false); f.frame(12);
  f.ctx.mA11yBuildCursor = true;
  assert.equal(f.ctx.mA11yBuildProduct, null);
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
  assert.equal(f.selects.length, 0);
});

check('a tool or mode change after the modal closed invalidates the memory, even in the same millisecond', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.modalRound('ours-first');
  f.ctx.A11yBuildProductDropped(0);                                // same tick as the menu action arrives
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
  assert.equal(f.ctx.mA11yBuildProduct, null);
  assert.equal(f.selects.length, 0);
  const g = fixture();
  g.ctx.A11yBuildProductSelected({product: g.product()});
  g.modalRound('ours-first');
  g.ctx.A11yBuildProductDropped(0); g.frame(1);                    // finalized by the next frame
  assert.equal(g.ctx.mA11yBuildProduct, null);
});

check('an unrelated modal much earlier does not resurrect a stale product', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.modalRound('ours-first');
  f.frame(Math.ceil(runtime.A11Y_PRODUCT_RESTORE_WINDOW / 16) + 1); // the window elapsed before any menu action
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
  assert.equal(f.ctx.mA11yBuildProduct, null);
});

check('nested modals: nothing restores until the balance is back to zero', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.ctx.A11yBuildProductModal(true); f.ctx.A11yBuildProductDropped(0);
  f.ctx.A11yBuildProductModal(true);                               // a second modal on top
  f.frame(10);
  f.ctx.A11yBuildProductModal(false);
  f.ctx.mA11yBuildCursor = true;
  assert.equal(f.ctx.A11yBuildProductRestore(), false);            // one still open: memory kept
  assert.notEqual(f.ctx.mA11yBuildProduct, null);
  f.ctx.A11yBuildProductModal(false); f.frame(1);
  assert.equal(f.ctx.A11yBuildProductRestore(), true);
});

check('restore needs the cursor back and no modal; a failing native select forgets', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.modalRound('ours-first');
  f.ctx.mA11yBuildCursor = false;                                  // the resume did not enable the cursor
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
  assert.equal(f.selects.length, 0);
  const g = fixture();
  g.ctx.A11yBuildProductSelected({product: g.product({Select() { throw new Error('gone'); }})});
  g.modalRound('ours-first');
  assert.equal(g.ctx.A11yBuildProductRestore(), false);
  assert.equal(g.ctx.mA11yBuildProduct, null);
});

check('a new selection resets the memory; forget clears everything but the modal balance', () => {
  const f = fixture();
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.modalRound('ours-first');
  const p = f.product({stateIndex: 1});
  f.ctx.A11yBuildProductSelected({product: p});                    // the player picked something else
  assert.equal(f.ctx.mA11yBuildProductLost, false);
  assert.equal(f.ctx.A11yBuildProductRestore(), false);
  f.ctx.A11yBuildProductModal(true);
  f.ctx.A11yBuildProductForget();
  assert.equal(f.ctx.mA11yBuildProduct, null);
  assert.equal(f.ctx.mA11yBuildProductClosedAt, 0);
  assert.equal(f.ctx.mA11yBuildProductModals, 1);
});

check('frames with nothing pending and drops with nothing remembered are no-ops', () => {
  const f = fixture();
  f.frame(3);
  f.ctx.A11yBuildProductDropped(0);
  assert.equal(f.ctx.mA11yBuildProductDropPending, false);
  f.ctx.A11yBuildProductSelected({product: f.product()});
  f.frame(3);
  assert.notEqual(f.ctx.mA11yBuildProduct, null);
});


check('Selected definition id remains a full decimal string and invalid products clear it', () => {
 const f=fixture();const id='18446744073709551601';
 f.ctx.A11yBuildProductSelected({product:f.product({resourceKey:{instance:id},Name:'Bed | test'})});
 assert.deepStrictEqual(f.posts,[['a11y.buildproduct',id+'|Bed%20%7C%20test']]);
 f.ctx.A11yBuildProductForget();assert.equal(f.posts.length,1);
 f.ctx.A11yBuildProductSelected({product:null});assert.deepStrictEqual(f.posts[1],['a11y.buildproduct','0|']);
});

check('Hand cancellation completes before matching ack and forgets restoration',()=>{
 const f=fixture(),events=[];f.ctx.mA11yKeyboardLease=20000;
 f.ctx.A11yWorldHudMode=()=>2;f.ctx.A11yBuildToolAllowed=()=>true;
 runtime.CommunicationManager.CallGameService=name=>events.push(name);
 runtime.CommunicationManager.SendUIMessage=name=>events.push(name);
 f.ctx.A11yPostToPython=(cmd,payload)=>events.push(cmd+':'+payload);
 f.ctx.mA11yBuildProduct=f.product();method('A11yBuildHandDrop').call(f.ctx,'73');
 assert.deepStrictEqual(events,['BBCancelUserTool','BBInspectorHideMoveToolPanel','a11y.buildhand:73|ok']);
 assert.equal(f.ctx.mA11yBuildProduct,null);
});
check('Invalid handoff owners refuse without cancelling',()=>{
 for(const mutate of [f=>f.ctx.blocked=true,f=>f.ctx.mA11yKeyboardLease=1,f=>f.ctx.mA11yBuildControls=false,f=>f.ctx.mA11yKeyboard=false,f=>f.ctx.A11yBuildToolAllowed=()=>false,f=>f.ctx.A11yWorldHudMode=()=>1]){
 const f=fixture();f.ctx.mA11yKeyboardLease=20000;f.ctx.A11yWorldHudMode=()=>2;f.ctx.A11yBuildToolAllowed=()=>true;let cancelled=0;
 runtime.CommunicationManager.CallGameService=()=>cancelled++;
 mutate(f);method('A11yBuildHandDrop').call(f.ctx,'74');
 assert.equal(cancelled,0);assert.deepStrictEqual(f.posts,[['a11y.buildhand','74|denied']]);
 }
});
check('Native cancellation exception is denied',()=>{
 const f=fixture();f.ctx.mA11yKeyboardLease=20000;f.ctx.A11yWorldHudMode=()=>2;f.ctx.A11yBuildToolAllowed=()=>true;
 runtime.CommunicationManager.CallGameService=()=>{throw Error('native');};
 method('A11yBuildHandDrop').call(f.ctx,'75');assert.deepStrictEqual(f.posts,[['a11y.buildhand','75|denied']]);
});
console.log(checks + ' checks passed (' + path.basename(SOURCE) + ')');
