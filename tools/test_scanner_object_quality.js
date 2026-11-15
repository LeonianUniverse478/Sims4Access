'use strict';
// Run the scanner's Flash methods with the native metadata and localisation services stubbed.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../flash/TooltipManager_patched.as'), 'utf8');

function method(name, context) {
    const signature = new RegExp('public function ' + name + '\\(([^)]*)\\)\\s*:\\s*\\w+\\s*\\{').exec(source);
    assert(signature, name);
    const start = signature.index + signature[0].length;
    let end = start, depth = 1;
    while (depth && end < source.length) {
        const character = source[end++];
        if (character === '{') depth++;
        if (character === '}') depth--;
    }
    assert.strictEqual(depth, 0);
    const strip = text => text.replace(/:\s*(?:Boolean|String|Object|Class|Array|Error|int)\b(?!\s*\()/g, '')
        .replace(/\s+as Class\b/g, '').replace(/ is Array\b/g, ' instanceof Array');
    return vm.runInContext('(function(' + strip(signature[1]) + '){' + strip(source.slice(start, end - 1)) + '})', context);
}

const id = '18446744073709551615';
let data, rules, skills, requests, replies, timers, checks = 0;
const label = text => ({toString() { return text; }});
const gameKeys = {
    HOVERTIP_QUALITY: label('Jakość:'),
    HOVERTIP_ONE_STAR: label('first tier'), HOVERTIP_TWO_STAR: label('second tier'),
    HOVERTIP_THREE_STAR: label('third tier'), GARDENING_QUALITY_FORMER: {toString: value => 'former ' + value}
};
const classes = {
    'gamedata.Gameplay.shared.definitions.HoverTipStaticData': {
        GetHoverTipStaticDataForStyle(style) { assert.strictEqual(style, String(data.hover_tip)); return rules; }
    },
    'gamedata.Gameplay.shared.GameplayStateData': {get AllSkillProgressUpdates() { return skills; }},
    'olympus.objects.ObjectMetadata': class {
        constructor(fields) {
            this.quality = fields.quality || 0;
            this.quality_description = fields.quality_description || null;
            this.evolution_progress = fields.evolution_progress;
        }
    },
    'olympus.localization.KeysGP': gameKeys,
    'olympus.localization.Keys': {GENERIC_SPACE: {toString: (heading, value) => heading + ' ' + value}}
};
const context = vm.createContext({
    Array, String, int: value => value | 0, encodeURIComponent,
    getDefinitionByName(name) { assert(Object.hasOwn(classes, name), name); return classes[name]; },
    CommunicationManager: {CallGameService(service, objectId, requestMetadata) {
        assert.deepStrictEqual([service, objectId, requestMetadata], ['GetObjectMetadata', id, true]);
        requests++;
        if (data instanceof Error) throw data;
        return data;
    }},
    setTimeout(callback, delay, ...args) { assert.strictEqual(delay, 50); timers.push(() => callback(...args)); }
});
const owner = {A11yPostToPython(command, payload) { replies.push([command, payload]); }};
owner.A11yObjectQualityText = method('A11yObjectQualityText', context);
owner.A11yObjectQuality = method('A11yObjectQuality', context).bind(owner);

function begin(record, restrictions = [], progress = []) {
    data = record; rules = restrictions; skills = progress; requests = 0; replies = []; timers = [];
    owner.A11yObjectQuality('31', id);
}
function expect(text, calls = 1) {
    assert.strictEqual(requests, calls);
    assert.deepStrictEqual(timers, []);
    assert.deepStrictEqual(replies, [['a11y.objectquality_enc', '31|' + id + '|' + encodeURIComponent(text)]]);
    checks++;
}

for (const style of [1, 2, 4, 5, 7, 8]) {
    begin({hover_tip: style, quality: 2, rarity_text: label('rare')}); expect('Jakość: second tier');
}
for (const [tier, expected] of [[1, 'Jakość: first tier'], [3, 'Jakość: third tier'], [9, '']]) {
    begin({hover_tip: 2, quality: tier}); expect(expected);
}
const tokenised = {tokens: ['świeży', 'napój'], toString() { return '<b>' + this.tokens.join('|') + '</b>'; }};
begin({hover_tip: 2, quality: 1, quality_description: tokenised});
expect('Jakość: <b>świeży|napój</b>');
begin({hover_tip: 4, quality: 0, rarity_text: label('rare')}); expect('');
begin({hover_tip: 6, quality: 2}); expect('');
begin({hover_tip: 3, quality: 4, quality_description: label('perfect')}); expect('Jakość: perfect');
begin({hover_tip: 3, quality: 4, quality_description: label('perfect'), evolution_progress: 1});
expect('Jakość: former perfect');
begin({hover_tip: 3, quality: 0, quality_description: label('wild'), recipe_name: label('plant')}); expect('');
begin({hover_tip: 3, quality: 2}); expect('');

const guarded = Object.freeze({hover_tip: 2, quality_description: label('special'), quality: 1});
const restrictions = ['quality_description', 'quality'].map(field_name => ({field_name, skill_id: '7', skill_points: 5}));
begin(guarded, restrictions, [{skill_id: '7', curr_points: 4}]); expect('');
begin(guarded, restrictions, [{skill_id: '7', curr_points: 5}]); expect('Jakość: special');
begin(guarded, restrictions, [{skill_id: '8', curr_points: 0}]); expect('Jakość: special');
assert.strictEqual(guarded.quality_description.toString(), 'special');

begin(null);
assert.deepStrictEqual(replies, []); assert.strictEqual(timers.length, 1);
data = {hover_tip: 2, quality: 1}; timers.shift()(); expect('Jakość: first tier', 2);
for (const record of [null, {hover_tip: 0}, {hover_tip: 2}]) {
    begin(record); assert.strictEqual(timers.length, 1); timers.shift()(); expect('', 2);
}
begin(new Error('missing service')); expect('');
requests = 0; replies = []; timers = [];
owner.A11yObjectQuality('bad|serial', id); owner.A11yObjectQuality('31', '0x200'); owner.A11yObjectQuality('31', '0');
assert.deepStrictEqual([requests, replies.length, timers.length], [0, 0, 0]); checks++;
assert(source.includes('_loc3_ == "objectquality" && _loc2_.length == 4') &&
    source.includes('this.A11yObjectQuality(String(_loc2_[2]),String(_loc2_[3]))')); checks++;
console.log(checks + ' scanner object quality checks passed');
