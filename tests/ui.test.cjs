// Pure rendering/interaction logic tests. These do not substitute for browser layout checks.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const fixture=JSON.parse(fs.readFileSync('test-results/ui-fixture.json','utf8'));
function context(hash='#overview'){
  const elements=new Map(); const listeners={};
  const doc={querySelector(selector){if(!elements.has(selector))elements.set(selector,{innerHTML:'',className:'',textContent:'',value:'',focus(){},setSelectionRange(){}});return elements.get(selector);},querySelectorAll(){return [];},addEventListener(type,fn){listeners[type]=fn;}};
  const ctx=vm.createContext({document:doc,window:{addEventListener(){},scrollTo(){}},location:{hash},localStorage:{getItem(){return 'alex';},setItem(){}},URLSearchParams,Date,Number,JSON,console,setTimeout,clearTimeout,fetch(){throw Error('Unexpected network in rendering test');}});
  const source=fs.readFileSync('web/experience.js','utf8')+'\n'+fs.readFileSync('web/app.js','utf8').replace(/\nload\(\);\s*$/,'');
  vm.runInContext(source,ctx);
  ctx.fixture=structuredClone(fixture);
  vm.runInContext('app.data=fixture.seed; app.detail=fixture.hero;',ctx);
  return {ctx,elements,listeners,run:code=>vm.runInContext(code,ctx)};
}
for(const page of ['overview','orders','trust','studio','lab','guide'])test(`renders ${page} with actual pipeline data`,()=>{const c=context('#'+page);c.run('render()');const html=c.elements.get('#main').innerHTML;assert.ok(html.length>1000);assert.ok(!html.includes('undefined'));assert.ok(!html.includes('NaN'));assert.ok(!html.includes('[object Object]'));});
test('KPI display reconciles with selected period',()=>{const c=context();const html=c.run('overview()');assert.ok(html.includes('86,880'));assert.ok(html.includes('115 completed orders'));assert.ok(html.includes('33.9%'));});
test('held orders never show a fake zero quantity',()=>{const c=context('#orders');const html=c.run('orderTable([fixture.hero.fact],true)');assert.ok(html.includes('Evidence held'));assert.ok(html.includes('Unknown'));assert.ok(html.includes('>—</td>'));});
test('hero impact explicitly distinguishes naive age from elapsed time',()=>{const c=context();const html=c.run('impactView(fixture.hero)');for(const text of ['480','190','720','Not yet applied','Not a valid completed duration'])assert.ok(html.includes(text));});
test('incomplete order says not yet observed and no linked incident',()=>{const c=context();const html=c.run('orderView(fixture.open)');assert.ok(html.includes('Not yet observed'));assert.ok(html.includes('No linked incident'));});
test('non-hero investigation has its own evidence',()=>{const c=context('#studio/DQ-WO-2631');c.run('app.detail=fixture.other');const html=c.run('studio()');assert.ok(!html.includes('140-minute'));assert.ok(!html.includes('BUF-1042'));assert.ok(html.includes('violates the rules listed below'));});
test('viewer cannot acknowledge through enabled controls',()=>{const c=context('#studio/INC-1042');const html=c.run("app.actor='jules'; reviewView(fixture.hero,fixture.hero.incidents[0])");assert.match(html,/value="acknowledge" disabled/);});
test('operator proposes but cannot approve or resolve',()=>{const c=context();let html=c.run("reviewView(fixture.acknowledge,fixture.acknowledge.incidents[0])");assert.match(html,/value="propose" >/);assert.match(html,/value="resolve" disabled/);html=c.run("reviewView(fixture.propose,fixture.propose.incidents[0])");assert.match(html,/value="approve" disabled/);});
test('independent supervisor can approve',()=>{const c=context();const html=c.run("app.actor='sam'; reviewView(fixture.propose,fixture.propose.incidents[0])");assert.match(html,/value="approve" >/);});
test('resolved view reports applied evidence and allows reopening',()=>{const c=context();c.run("app.actor='sam'; app.data=fixture.resolved_state");const html=c.run('reviewView(fixture.resolve,fixture.resolve.incidents[0])');assert.ok(html.includes('Applied with approval'));assert.ok(html.includes('Reopen investigation'));});
test('search and evidence filter work together',()=>{const c=context('#orders');c.run("app.search='1042'; app.trust='held'");const html=c.run('orders()');assert.ok(html.includes('1 matching orders'));assert.ok(!html.includes('WO-2639'));});
test('empty search is a usable state',()=>{const c=context('#orders');c.run("app.search='no-such-order'");assert.ok(c.run('orders()').includes('No orders match'));});
test('all 72-day pagination is bounded',()=>{const c=context('#orders');c.run('app.page=999');c.run('orders()');assert.equal(c.run('app.page'),6);});
test('notes and source strings are escaped against HTML injection',()=>{const c=context();assert.equal(c.run("e('<img src=x onerror=alert(1)>')"),'&lt;img src=x onerror=alert(1)&gt;');c.run("fixture.hero.events[0].event_id='<script>evil()</script>'");const html=c.run('sources(fixture.hero)');assert.ok(!html.includes('<script>evil'));assert.ok(html.includes('&lt;script&gt;'));});
test('handover links to evidence and has no inferred cause',()=>{const c=context();const html=c.run('handover()');assert.ok(html.includes('/api/export?'));assert.ok(html.includes('#studio/INC-1042'));assert.ok(html.includes('does not identify the cause'));});
test('method metrics use computed fixture scores',()=>{const c=context();const html=c.run('lab()');assert.ok(html.includes('50%'));assert.ok(html.includes('100%'));assert.ok(html.includes('205 held-out orders'));});
test('date filter rejects reversed interval',()=>{const c=context();const target={id:'date-from',value:'2026-12-01'};c.listeners.change({target});assert.equal(c.run('app.filters.from'),'2026-11-02');assert.equal(target.value,'2026-11-02');});
test('product-name search matches readable labels',()=>{const c=context('#orders');c.run("app.search='buffer solution'");const html=c.run('orders()');assert.ok(html.includes('WO-1042'));assert.ok(!html.includes('WO-2640'));});
test('recovered hero does not keep claiming its completion is missing',()=>{const c=context();c.run('app.data=fixture.resolved_state');const html=c.run('overview()');assert.ok(html.includes('Evidence restored'));assert.ok(!html.includes('WO-1042 looks 480 minutes old'));});
test('empty filtered scope does not erase the global hero state',()=>{const c=context();c.run('app.data=fixture.resolved_state;app.data.incidents=[]');const html=c.run('overview()');assert.ok(html.includes('Evidence restored'));assert.ok(html.includes('outside the current filter scope'));});

test('handover includes every incident and all held orders without truncation',()=>{
  const c=context();const html=c.run('handover()');
  for(const i of fixture.seed.incidents)assert.ok(html.includes('#studio/'+i.id),i.id);
  for(const f of fixture.seed.facts.filter(f=>f.trust==='held'))assert.ok(html.includes('#orders/'+f.order_id),f.order_id);
  assert.ok(html.indexOf('INC-1043')<html.indexOf('DQ-WO-'));
  assert.ok(html.includes('no truncation'));assert.ok(html.includes('not actual loss'));
});
test('handover preserves human step, references and uncertainty after recovery',()=>{
  const c=context();c.run('app.data=fixture.handover_state');const html=c.run('handover()');
  assert.ok(html.includes('Sam Chen'));assert.ok(html.includes('compare the material handoff timestamps'));
  assert.ok(html.includes('R-WO-1042-2'));assert.ok(html.includes('Completion not verified'));
  assert.ok(!html.includes('#studio/INC-1042'));assert.ok(html.includes('Complete held-order register (5)'));
});
test('handover exposes outside-scope count and category empty states',()=>{
  const c=context();c.run("app.data.handover.operational=[];app.data.handover.data=[];app.data.handover.held=[];app.data.handover.open_count=0;app.data.handover.outside_scope=7");
  const html=c.run('handover()');assert.ok(html.includes('7 outside this scope'));assert.ok(html.includes('Include all dates, stations and shifts'));assert.ok(html.includes('No unresolved incidents'));assert.ok(html.includes('No held orders'));
});
test('duplicate timeline never paints recorded events as validated',()=>{
  const c=context();const html=c.run('timeline(fixture.duplicate)');
  assert.equal((html.match(/Evidence held/g)||[]).length,4);assert.ok(!html.includes('✓'));
  assert.ok(html.includes('2 source copies'));assert.ok(html.includes('DUPLICATE'));
  assert.ok(c.run('orderView(fixture.duplicate)').includes('Suggested evidence checks · not completed actions'));
});
test('recovery timeline requires approved evidence for its recovered label',()=>{
  const c=context();assert.ok(!c.run('timeline(fixture.hero)').includes('Recovered · approved'));
  assert.ok(c.run('timeline(fixture.approve)').includes('Recovered · approved'));
  assert.ok(c.run('timeline(fixture.open)').includes('Recorded · prefix checked'));
});
test('operational review emphasizes its own context rather than recovery proposal',()=>{
  const c=context('#studio/INC-1043');c.run("app.detail=fixture.operational;app.tab='review'");const html=c.run('studio()');
  assert.ok(html.includes('Record next step'));assert.ok(html.includes('Missing information'));
  assert.ok(html.includes('Related investigations · separate decisions'));assert.ok(html.includes('#studio/INC-1042'));
  assert.ok(!html.includes('Recovery review record'));assert.ok(!html.includes('BUF-1042'));assert.ok(!html.includes('+720'));
});
test('incident audit isolates current incident but retains related history in payload',()=>{
  const c=context('#studio/INC-1043');c.run("app.detail=fixture.operational;app.tab='audit'");const html=c.run('studio()');
  assert.ok(html.includes('Current incident only'));assert.ok(html.includes('material handoff'));
  assert.ok(!html.includes('BUF-1042'));assert.ok(fixture.operational.audit.some(a=>a.entity==='INC-1042'));
});
test('operational closure form requires outcome, uncertainty and explicit confirmation',()=>{
  const c=context();const html=c.run("app.actor='sam';reviewView(fixture.operational,fixture.operational.incidents.find(i=>i.id==='INC-1043'))");
  for(const field of ['closure-outcome','closure-note','uncertainty','action-taken','confirm-resolution'])assert.ok(html.includes('id="'+field+'"'));
  assert.match(html,/id="confirm-resolution" required/);assert.ok(html.includes('Cause remains unestablished'));
  assert.ok(!html.includes('value="resolve"'));assert.ok(html.includes('Confirm operational closure'));
});
test('viewer cannot record a next step or close operational investigation',()=>{
  const c=context();const html=c.run("app.actor='jules';reviewView(fixture.operational,fixture.operational.incidents[1])");
  assert.match(html,/disabled>Record next step/);assert.match(html,/disabled>Confirm operational closure/);
});
test('recovered Data Trust labels 480-minute comparison as historical',()=>{
  const c=context();c.run('app.data=fixture.resolved_state');const html=c.run('trust()');
  assert.ok(html.includes('RECOVERY APPLIED · HISTORICAL COMPARISON'));assert.ok(html.includes('not a current unresolved delay'));
  assert.ok(html.includes('720 units included'));assert.ok(!html.includes('CURRENT REPORTING GAP'));
});
test('Method Lab renders stress errors, thresholds, imbalance and unavailable cases',()=>{
  const c=context();const html=c.run('lab()');
  for(const text of ['Perfect on one seed is not enough','6,000','False positives','Missed','Low sample','Zero MAD','Rare deviations','Threshold sensitivity','false positive','false negative','Unscored'])assert.ok(html.includes(text),text);
});
test('human plan content is escaped in review and handover',()=>{
  const c=context();c.run("app.data=fixture.handover_state;app.data.handover.operational[0].plan.next_action='<img src=x onerror=alert(1)>'");
  assert.ok(c.run('handover()').includes('&lt;img'));assert.ok(!c.run('handover()').includes('<img src=x'));
});
test('keyboard arrows select an investigation tab and preserve focus',()=>{
  const c=context('#studio/INC-1042');let prevented=false;
  c.listeners.keydown({target:{getAttribute:()=> 'tab'},key:'ArrowRight',preventDefault(){prevented=true;}});
  assert.equal(c.run('app.tab'),'review');assert.equal(prevented,true);
  assert.ok(c.run('studio()').includes('aria-labelledby="tab-review"'));
});
test('resolution submit sends structured fields and only checked references',()=>{
  const c=context();c.run("app.currentIncident=fixture.operational.incidents[1];mutate=(action,body)=>{globalThis.sent={action,body};}");
  for(const [id,value] of Object.entries({'closure-note':'An evidence-based closure rationale with remaining uncertainty.','closure-outcome':'administratively_closed','uncertainty':'The cause remains unknown pending station records.','action-taken':''}))c.ctx.document.querySelector('#'+id).value=value;
  c.ctx.document.querySelector('#confirm-resolution').checked=true;
  c.listeners.submit({preventDefault(){},target:{id:'resolution-form',reportValidity:()=>true,querySelectorAll:()=>[{value:'R-WO-1042-2'}]}});
  assert.equal(c.ctx.sent.action,'resolve');assert.equal(c.ctx.sent.body.confirm_resolution,true);assert.equal(c.ctx.sent.body.refs[0],'R-WO-1042-2');assert.equal(c.ctx.sent.body.incident_id,'INC-1043');
});
test('server errors appear inline and release busy state without discarding form',async()=>{
  const c=context();const inline={textContent:'',focus(){this.focused=true;}};c.ctx.form={querySelector:()=>inline};
  await c.run("mutate('plan',{},form)");assert.ok(inline.textContent.includes('Unexpected network'));assert.equal(inline.focused,true);assert.equal(c.run('app.busy'),false);
});
test('new findings after approved recovery retain history but show current exclusion',()=>{
  const c=context();c.run("app.data=fixture.resolved_state;app.data.featured_recovery_approved=true;app.data.featured_fact.trust='held'");
  const html=c.run('trust()');assert.ok(html.includes('APPROVAL RETAINED · NEW DATA HOLD'));assert.ok(!html.includes('720 units included'));
  assert.ok(c.run('overview()').includes('New findings need review'));
});
test('trust coverage uses actual closed denominator when an open order is held',()=>{
  const c=context();c.run('app.data.global_metrics.held=7;app.data.global_metrics.closed=643');
  const html=c.run('trust()');assert.ok(html.includes('637 / 643 closed orders'));assert.ok(!html.includes('637 / 644 closed orders'));
});
