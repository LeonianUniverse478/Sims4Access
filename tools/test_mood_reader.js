'use strict';
// Control Alt E: TooltipManager.A11yMood hands the reading to SimHub's
// MoodContainer by name (or posts an empty, unavailable reply), and
// MoodContainer posts one a11y.mood_enc record per moodlet with every
// BuffTooltip field. Logic only; the gates and live tests prove the movie.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const tm=fs.readFileSync(path.join(__dirname,'../flash/TooltipManager_patched.as'),'utf8');
const mc=fs.readFileSync(path.join(__dirname,'../flash/extra-classes/MoodContainer.as'),'utf8');
function method(source,name,globals){
 const sig=new RegExp('public function '+name+'\\(([^)]*)\\)\\s*:\\s*[\\w.<>]+\\s*\\{').exec(source);assert(sig,name);
 let start=sig.index+sig[0].length,at=start,depth=1;
 while(depth){if(source[at]==='{')depth++;if(source[at]==='}')depth--;at++;}
 const strip=s=>s.replace(/(\w):(Vector\.<\w+>|\*|\w+)/g,'$1').replace(/\s+as\s+DisplayObject\b/g,'');
 return vm.runInNewContext('(function('+strip(sig[1]).replace(/\s*=\s*null/g,'')+'){'+strip(source.slice(start,at-1))+'})',
   Object.assign({String,int:x=>x|0,encodeURIComponent},globals||{}));
}
let checks=0;

// TooltipManager side.
for(const [label,state,expectRead,expectPosts] of [
 ['live hub reads',{keyboard:true,hub:true},1,[]],
 ['hidden hub is unavailable',{keyboard:true,hub:false},0,[['a11y.mood_enc','']]],
 ['keyboard off stays silent',{keyboard:false,hub:true},0,[]],
 ['a modal keeps the key',{keyboard:true,hub:true,modal:true},0,[]],
]){
 let reads=0;const posts=[];
 const hub=state.hub?{mcMoodContainer:{A11yReadMood:()=>{reads++;}}}:null;
 method(tm,'A11yMood').call({mA11yKeyboard:state.keyboard,mA11yActiveModalRoot:state.modal?{}:null,
   A11yLoadedWidget:()=>hub,A11yIsLive:o=>!!o,A11yPostToPython:(c,p)=>posts.push([c,p])});
 assert.strictEqual(reads,expectRead,label);assert.deepStrictEqual(posts,expectPosts,label);checks++;
}
assert(/"a11y\.clock_enc","a11y\.mood_enc"/.test(tm),'startup allow list');checks++;

// MoodContainer side.
const moods={happy:{GetMoodName:()=>'Happy'},tense:{GetMoodName:()=>'Tense'}};
const loc=f=>({IsValid:()=>true,toString:f});
const globals={
 MoodStaticData:{GetMoodByKey:k=>moods[k]||null},
 KeysGP:{SIM_HUB_BUFF_TITLE:loc((m,w)=>m+' +'+w),SIM_HUB_BUFF_BOOST:loc(m=>'Boosting: '+m)},
 Keys:{GENERIC_TIMESPAN:loc(m=>m+' minutes')},
 BuffStaticData:{GetStaticData:id=>id==='99'?{name:loc(()=>'Relieved')}:null},
 GameplayStateData:{ActiveSimToken:{},AllBuffInfo:null},sA11yMoodSeq:0,
 TimeSpan:function(){this.Set=ms=>{this.ms=ms;};this.ConvertToMinutes=()=>Math.floor(this.ms/60000);},
 TextField:function(){let t='';Object.defineProperty(this,'htmlText',{set:v=>{t=v.replace(/<[^>]*>/g,'');}});Object.defineProperty(this,'text',{get:()=>t});},
};
const posts=[];
globals.TooltipManager={getInstance:()=>({A11yPostToPython:(c,p)=>posts.push([c,decodeURIComponent(p)])})};
const self={mCurrentMood:{mood_intensity:1,mood_key:'happy'},mCurrentMoodData:{GetMoodName:i=>'Very Happy'},
 mA11yMoodDescription:'<b>Feeling</b> good (really!)'};
for(const name of ['A11yReadMood','A11yBuffRecord','A11yBuffTime','A11yPlain','A11yPostMood']){self[name]=method(mc,name,globals);}

globals.GameplayStateData.AllBuffInfo=[
 {mood_weight:1,MoodKey:'happy',StaticMoodKey:'happy',mood_type_override:null,Name:'Had a Great Meal',
  Reason:'(From Eating)',Description:'Delicious.',timeout:'123',TimeLeft:3*60*60000,transition_into_buff_id:'0',
  TimeoutString:loc(m=>'Expires in '+m),TimeoutStringNoNextBuff:{IsValid:()=>false}},
 {mood_weight:2,MoodKey:'happy',StaticMoodKey:'tense',mood_type_override:'happy',Name:'Pumped',
  Reason:'',Description:'Long description\u0001with separator.',timeout:'5',TimeLeft:600000,transition_into_buff_id:'99',
  TimeoutString:loc((m,n)=>'Becomes '+n+' in '+m),TimeoutStringNoNextBuff:{IsValid:()=>false}},
 {mood_weight:0,MoodKey:'0',StaticMoodKey:'0',mood_type_override:null,Name:'Neutral',Reason:'',Description:'',timeout:'0'}];
self.A11yReadMood();
const S='\u0001';
assert(posts.every(p=>p[0]==='a11y.mood_enc'));checks++;
assert.deepStrictEqual(posts.map(p=>p[1]),[
 ['M','1','3','happy','Very Happy','Feeling good (really!)'].join(S),
 ['B','1','0','happy','0','1','Had a Great Meal','Happy +1','','(From Eating)','Expires in 180','Delicious.'].join(S),
 ['B','1','1','happy','1','2','Pumped','Tense +2','Boosting: Happy','','Becomes Relieved in 10','Long description with separator.'].join(S),
 ['B','1','2','0','0','0','Neutral','','','','',''].join(S),
 ['E','1'].join(S)]);checks++;
// A second press is a new reading, and the long field is capped last.
posts.length=0;globals.GameplayStateData.AllBuffInfo=[Object.assign({},{mood_weight:1,MoodKey:'happy',mood_type_override:null,
 Name:'Wordy',Reason:'(Why)',Description:'x'.repeat(3000),timeout:'0'})];
self.A11yReadMood();
assert.strictEqual(posts[0][1].split(S)[1],'2');checks++;
assert.strictEqual(posts[1][1].length,1400);assert(posts[1][1].startsWith(['B','2','0','happy','0','1','Wordy'].join(S)));checks++;
// A broken moodlet is skipped and the reading still ends.
posts.length=0;globals.GameplayStateData.AllBuffInfo=[{get mood_weight(){throw new Error('bad');}}];
self.A11yReadMood();
assert.deepStrictEqual(posts.map(p=>p[1].split(S)[0]),['M','E']);checks++;
// Never ++ or -- in added code: the integer gate counts them.
const added=mc.slice(mc.indexOf('public function A11yReadMood'),mc.indexOf('protected function IsPhoneAlertVisible'));
assert(!/\+\+|--/.test(added),'no increment operators in added code');checks++;
console.log(checks+' mood reader checks passed');
