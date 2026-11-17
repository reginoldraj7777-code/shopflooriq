'use strict';
// Evidence-focused presentation. The main controller owns state and requests.
function sourceLinks(refs, orderId) {
  return refs.map(ref => `<a class="evidence-ref" href="#orders/${e(orderId)}" title="Inspect source rows for ${e(orderId)}">${e(ref)}</a>`).join(' ');
}

function timelineView(detail) {
  const titles = {start:'Order started', fill:'Filling finished', pack:'Packing started', complete:'Order completed'};
  return `<p class="small muted">Recorded is not the same as validated. A blocking finding holds the entire order out of KPIs.</p><div class="timeline">${detail.steps.map(step => {
    const v = step.events[0];
    const valid = ['Validated','Recovered · approved'].includes(step.status);
    return `<div class="timeline-step ${valid?'validated':v?'held':'missing'}"><div class="node" aria-hidden="true">${valid?'✓':v?'!':'?'}</div><b>${titles[step.kind]}</b><small>${v?time(v.event_time):step.status}</small><strong class="step-state">${e(step.status)}</strong><small class="mono">${v?e(v.event_id):'No trusted timestamp'}</small>${step.events.length>1?badge(step.events.length+' source copies','amber'):''}${step.findings.length?`<small>${e([...new Set(step.findings.map(f=>f.rule))].join(' · '))}</small>`:''}</div>`;
  }).join('')}</div>`;
}

function investigationHints(detail) {
  const rules = new Set(detail.findings.map(f=>f.rule));
  const hints=[];
  if(rules.has('DUPLICATE')) hints.push('Compare every source copy of the repeated event ID, including receipt time and quantity. Establish which source record is authoritative before requesting a correction.');
  if(rules.has('SEQUENCE')||rules.has('TIMESTAMP')) hints.push('Check raw step timestamps, offsets and event ordering against the source log. A displayed time is an observation, not proof of a valid sequence.');
  if(rules.has('UNIT')||rules.has('QUANTITY')) hints.push('Verify the source unit and completed count against the order. Do not assume a conversion or replace an invalid count with the plan.');
  if(rules.has('FRESHNESS')) hints.push('Compare event and receipt times to establish the transfer delay; request source-transfer evidence.');
  if(rules.has('MISSING_STEP')) hints.push('Request the missing source step and compare its identity and timestamps. The hero receipt has a separate independent review workflow.');
  if(!hints.length&&detail.findings.length) hints.push('Inspect the cited raw rows and request evidence for the failing validation rule.');
  return hints.length?`<div class="callout info mt"><b>Suggested evidence checks · not completed actions</b><ul>${hints.map(h=>`<li>${h}</li>`).join('')}</ul><p>Notes do not repair source evidence. General source correction is outside this demonstration.</p></div>`:'';
}

function contextPanel(detail, incident) {
  const plan=incident.plan;
  return `<article class="card panel"><div class="card-head"><h2>Investigation context</h2>${badge(incident.state==='resolved'?'Closed record':'Action needed',incident.state==='resolved'?'green':'amber')}</div>
    <dl class="dictionary"><dt>Assigned owner</dt><dd>${e(app.data.users[incident.owner]?.name||'Unassigned — acknowledge to take ownership')}</dd>
    <dt>Latest recorded review</dt><dd class="preserve-lines">${e(incident.note||'No human review recorded yet.')}</dd>
    <dt>Next investigation step</dt><dd>${plan?e(plan.next_action):'No structured next step recorded. Review the existing note above, then record a specific step in Human review.'}</dd>
    <dt>Missing information</dt><dd>${plan?e(plan.missing_info):incident.category==='operational'?'Station logs, material availability and handoff observations are not present in this dataset. Event timing alone cannot establish the cause.':'Authoritative source evidence for the findings below; a note cannot override validation.'}</dd>
    ${plan?`<dt>Linked evidence</dt><dd>${sourceLinks(plan.refs,detail.order.id)}</dd><dt>Plan provenance</dt><dd>Recorded by ${e(app.data.users[plan.actor]?.name||plan.actor)} · ${e(plan.at)} · audit #${plan.audit_id}. An intention, not proof of completed work.</dd>`:''}</dl>
    ${incident.resolution?`<div class="callout mt"><b>${incident.state==='resolved'?'Closure outcome':'Previous closure · investigation reopened'}: ${e(incident.resolution.outcome.replaceAll('_',' '))}</b><p>Cause not established. ${e(incident.resolution.uncertainty)}</p><p>${e(incident.resolution.action_taken)}</p>${sourceLinks(incident.resolution.refs,detail.order.id)}</div>`:''}
  </article>`;
}

function evidenceChoices(detail, selected=[]) {
  return `<fieldset class="evidence-choices"><legend>Evidence references · this order only</legend>${[...detail.events.map(v=>({id:v.row_id,label:v.kind})),...detail.checks.map(v=>({id:v.id,label:v.observation}))].map(v=>`<label><input type="checkbox" name="refs" value="${e(v.id)}" ${selected.includes(v.id)?'checked':''}><span>${e(v.id)} <small>${e(v.label)}</small></span></label>`).join('')}</fieldset>`;
}

function reviewPanel(detail, i) {
  const role=app.data.users[app.actor].role;
  const proposals=detail.proposals.filter(p=>p.incident_id===i.id);
  const pending=proposals.find(p=>p.status==='pending');
  const approved=proposals.some(p=>p.status==='approved');
  const canWork=['operator','supervisor','admin'].includes(role);
  const controls=[];
  if(i.state==='open') controls.push(['acknowledge','Acknowledge & take ownership',canWork]);
  if(i.state==='acknowledged') {
    controls.push(['note','Save investigation note',canWork]);
    if(i.id==='INC-1042'&&!pending&&!approved) controls.push(['propose','Propose receipt recovery',['operator','supervisor'].includes(role)]);
    if(pending) controls.push(['approve','Approve recovery',role==='supervisor'&&pending.actor!==app.actor],['reject','Reject proposal',role==='supervisor'&&pending.actor!==app.actor]);
    if(i.category==='data') controls.push(['resolve','Resolve data incident',role==='supervisor'&&!detail.findings.length]);
  }
  if(i.state==='resolved') controls.push(['reopen','Reopen investigation',['supervisor','admin'].includes(role)]);
  const related=detail.incidents.filter(v=>v.id!==i.id);
  return `<div class="review-grid"><div class="stack"><article class="card panel"><h2>Record a defensible decision.</h2><p class="small muted">Acting as ${e(app.data.users[app.actor].name)} · ${role}. All writes are checked by the server.</p>
    <form id="review-form" class="form mt"><label for="review-note">Evidence reviewed and decision</label><textarea id="review-note" required minlength="10" maxlength="2000" placeholder="Cite the source, describe what you verified, and record your decision."></textarea><p class="muted">10–2,000 characters. Resolution needs at least 40 characters and six distinct words. Reopening preserves evidence, earlier decisions and their uncertainty.</p><div class="form-error" role="alert"></div>${controls.map(([action,label,enabled])=>`<button class="button ${['propose','approve','acknowledge','resolve'].includes(action)?'primary':''}" type="submit" name="action" value="${action}" ${enabled?'':'disabled'}>${label}</button>`).join('')}</form>
    <p class="small muted">${role==='viewer'?'Viewer is read-only.':pending&&pending.actor===app.actor?'Independent review required. The proposer cannot approve their own evidence.':'Notes cannot override data holds. These are demonstration permissions, not authentication.'}</p></article>
    ${i.state==='acknowledged'?`<article class="card panel"><h2>Make the next step explicit.</h2><p class="small muted">Record an evidence-linked intention for the next shift. This does not certify that the work has been performed.</p><form id="plan-form" class="form mt"><label for="next-action">Next investigation step</label><textarea id="next-action" required minlength="30" maxlength="2000">${e(i.plan?.next_action||'')}</textarea><label for="missing-info">Missing information / question to answer</label><textarea id="missing-info" required minlength="30" maxlength="2000">${e(i.plan?.missing_info||'')}</textarea>${evidenceChoices(detail,i.plan?.refs||[])}<div class="form-error" role="alert"></div><button class="button primary" type="submit" ${canWork?'':'disabled'}>Record next step</button></form></article>`:''}
    ${i.category==='operational'&&i.state==='acknowledged'?resolutionPanel(detail,role):''}</div><div class="stack">${contextPanel(detail,i)}
    ${i.category==='data'?`<article class="card panel"><h2>Recovery review record · ${e(i.id)}</h2>${proposals.length?proposals.map(p=>`<div class="finding"><div class="split"><span class="mono">${e(p.evidence_id)}</span>${badge(p.status,p.status==='approved'?'green':'amber')}</div><p>${e(p.note)}</p><p class="small muted">Proposed by ${e(app.data.users[p.actor]?.name||p.actor)}${p.reviewer?' · Reviewed by '+e(app.data.users[p.reviewer]?.name||p.reviewer):''}</p></div>`).join(''):`<p class="small muted">${i.id==='INC-1042'?'No proposal yet. Inspect BUF-1042 before proposing recovery.':'No supported automated recovery for this source defect. Request authoritative corrected evidence.'}</p>`}</article>`:''}
    ${related.length?`<aside class="callout info"><b>Related investigations · separate decisions</b>${related.map(v=>`<p><a href="#studio/${e(v.id)}">${e(v.id)} · ${e(v.title)}</a> ${stateBadge(v.state)}</p>`).join('')}<p>One incident’s approval or closure does not close another.</p></aside>`:''}</div></div>${i.id==='INC-1042'?impactView(detail):''}`;
}

function resolutionPanel(detail,role) {
  return `<article class="card panel"><details><summary class="resolution-summary">Close operational investigation · supervisor decision</summary><p class="small muted mt">Keep this open while investigation is ongoing. Closing does not establish a cause, release product or change KPIs. A supervisor may reopen it with a reason.</p>
  <form id="resolution-form" class="form mt"><label for="closure-outcome">Outcome</label><select id="closure-outcome" required><option value="">Choose an outcome</option value="administratively_closed">Administratively closed · no mitigation claimed</option><option value="mitigated">Mitigated · record action and verification</option></select>
  <label for="closure-note">Resolution rationale</label><textarea id="closure-note" required minlength="40" maxlength="2000"></textarea>
  <label for="uncertainty">Remaining uncertainty and follow-up</label><textarea id="uncertainty" required minlength="30" maxlength="2000"></textarea>
  <label for="action-taken">For mitigation: action taken and verification</label><textarea id="action-taken" maxlength="2000" placeholder="Required for a mitigated outcome; cite what was observed after the action."></textarea>
  ${evidenceChoices(detail)}<label class="checkbox-label"><input type="checkbox" id="confirm-resolution" required><span>I reviewed the evidence and remaining uncertainty, and intend to close this investigation. Cause remains unestablished.</span></label><div class="form-error" role="alert"></div><button class="button danger" type="submit" ${role==='supervisor'?'':'disabled'}>Confirm operational closure</button></form></details></article>`;
}

function handoverPanel() {
  const d=app.data,m=d.metrics,h=d.handover;
  function items(list) {
    return list.length?list.map(i=>`<article class="handover-item"><div class="split"><h3><a href="#studio/${e(i.id)}">${e(i.id)} · ${e(i.title)} →</a></h3>${stateBadge(i.state)}</div><p>Owner: <b>${e(d.users[i.owner]?.name||'Unassigned')}</b> · ${e(i.station)} / ${e(i.shift)} · <a href="#orders/${e(i.order_id)}">${e(i.order_id)}</a></p>
      ${i.plan?`<p><b>Recorded next step:</b> ${e(i.plan.next_action)}</p><p><b>Information needed:</b> ${e(i.plan.missing_info)}</p><p class="small muted">Recorded by ${e(d.users[i.plan.actor]?.name||i.plan.actor)} · audit #${i.plan.audit_id}. Completion not verified.</p>`:`<p><b>Next step not yet structured.</b> Review the recorded note and assign an evidence-linked step in Human review.</p>`}
      ${i.note?`<details><summary>Recorded review note · preserved verbatim</summary><p class="preserve-lines">${e(i.note)}</p></details>`:'<p class="muted">No human review recorded.</p>'}<details><summary>Evidence references · ${i.refs.length} raw rows</summary>${sourceLinks(i.plan?.refs||i.refs,i.order_id)}</details></article>`).join(''):'<p class="empty">No unresolved incidents in this category and scope.</p>';
  }
  return `<section class="handover mb" tabindex="-1" aria-label="Shift handover"><div class="split"><div><div class="eyebrow muted">EVIDENCE-BACKED HANDOVER</div><h2>What the next shift should know.</h2></div><button class="icon-button" data-action="close-handover" aria-label="Close handover">×</button></div>
    <p><b>${e(h.scope.from||'All dates')} – ${e(h.scope.to||'All dates')} · ${e(h.scope.station||'All stations')} · ${e(h.scope.shift||'All shifts')}</b><br><small>UTC · by order start · scenario clock ${e(d.as_of)}. Review timestamps are actual action time.</small></p>
    <p>${n(m.completed)} trusted orders / ${n(m.units)} units. ${m.held} held; ${m.incomplete} in progress. <a href="/api/export?${query()}">Inspect contributing rows</a>. ${m.late_count} trusted orders completed after plan; timing alone does not identify the cause.</p>
    <div class="callout info"><b>Priority logic:</b> ${e(h.ranking)}<br>${h.open_count} unresolved incidents shown, with no truncation. ${h.outside_scope} outside this scope. ${h.outside_scope?'<button class="button" data-action="all-handover">Include all dates, stations and shifts</button>':''}</div>
    <h3 class="mt">1 / Operational investigations (${h.operational.length})</h3>${items(h.operational)}
    <details class="handover-group" open><summary>2 / Data-quality investigations (${h.data.length})</summary>${items(h.data)}</details>
    <details class="handover-group"><summary>Complete held-order register (${h.held.length})</summary>${heldRegister(h.held)}</details>
    <p class="small muted">Deterministic summary of persisted records. Human plans are intentions, not verified corrective actions. No inferred causes or external transmission.</p></section>`;
}

function heldRegister(held) {
  return held.length?`<div class="table-wrap"><table class="table compact"><caption>All held orders, ranked by planned units; excluded from every production KPI</caption><thead><tr><th>Order</th><th>Plan · not actual loss</th><th>Blocking rules</th><th>Findings</th></tr></thead><tbody>${held.map(h=>`<tr><td><a href="#orders/${e(h.order_id)}">${e(h.order_id)}</a><br><small>${e(h.station)} · ${e(h.shift)}</small></td><td>${n(h.planned_units)} units</td><td>${e(h.rules.join(' · '))}</td><td>${h.findings}</td></tr>`).join('')}</tbody></table></div>`:'<p class="empty">No held orders in this scope.</p>';
}

function trustPage() {
  const d=app.data,m=d.global_metrics;
  return pageHead('ASSURANCE / DATA TRUST','Good decisions need good evidence.','A reconciled account of what contributes, what is held, and why.',`<a class="button" href="/api/source">${icon('download')} Export raw events</a><button class="button primary" data-action="refresh" ${d.users[app.actor].role==='admin'?'':'disabled'} title="Admin identity required">${icon('refresh')} Run validation</button>`)+
    `<div class="callout info mb">All 72 scenario days · all stations and shifts · independent of Mission Control filters. ${e(d.version)} · clock 15 Nov 2026, 14:00 UTC.</div>
    <div class="kpis trust-kpis">${[['Trusted completed',m.completed,`${n(m.units)} units contribute to KPIs`],['Held orders',m.held,'Units and durations unknown / excluded'],['In progress',m.incomplete,'Excluded; not automatically a data error'],['Closed-order coverage',pct(m.coverage),`${m.completed} / ${m.closed} closed orders`]].map(([label,value,foot])=>`<article class="card kpi"><div class="kpi-head">${label}</div><div class="kpi-value">${value}</div><p class="kpi-foot">${foot}</p></article>`).join('')}</div>
    <div class="trust-layout"><div class="stack"><article class="card panel"><div class="card-head"><h2>Prioritize the reporting gaps</h2>${badge(d.trust_impact.length+' held','amber')}</div><p class="small muted">Ranked by planned units descending, then order ID. Every held order excludes one order from duration and schedule denominators. Planned volume is exposure, not lost output, recoverable throughput or savings. Multiple findings can describe one defect.</p>${heldRegister(d.trust_impact)}</article>
    <article class="card"><div class="table-title"><div><h2>Ten explicit checks. No silent repairs.</h2><p>${n(d.source_rows)} raw rows · ${d.findings.length} findings · all raw evidence retained</p></div></div>${d.rules.map(r=>`<div class="rule-row"><span class="rule-icon ${r.count?'fail':''}">${r.count?'!':'✓'}</span><div class="rule-text"><strong>${e(r.id)}</strong><small>${e(r.name)}</small></div>${badge(r.count?r.count+' findings':'Pass',r.count?'amber':'green')}</div>`).join('')}</article></div>
    <div class="stack">${recoveryStatus()}<article class="card panel"><h2>Import a source-event batch</h2><p class="small muted">Admin only. JSON array, 1–5,000 rows / 2 MB. Identical row IDs are idempotent; conflicting rows reject the entire batch. Validation and audit update atomically.</p><input id="import-file" class="file-input" type="file" accept="application/json,.json" aria-label="Import synthetic source events" ${d.users[app.actor].role==='admin'?'':'disabled'}><p class="small muted">Only BUF-1042 has a supported correction workflow. Other seeded defects remain held. Source replacement and arbitrary data repair are not implemented.</p></article>
    ${d.orphan_events.length?`<article class="card panel"><h2>Unmatched source records</h2><p>These ${d.orphan_events.length} rows have no known order. They remain excluded and retained in the raw export.</p>${d.orphan_events.map(v=>`<p class="mono">${e(v.row_id)} · ${e(v.order_id||'missing order')}</p>`).join('')}</article>`:''}
    <div class="callout"><b>Incomplete is not incorrect.</b> Open work contributes no completed units or elapsed-time KPIs. Closed-order coverage excludes open work from its denominator.</div></div></div>`;
}

function recoveryStatus() {
  const recovered=app.data.featured_fact.trust==='trusted';
  if(app.data.featured_recovery_approved&&!recovered) return `<article class="hero"><div class="eyebrow">APPROVAL RETAINED · NEW DATA HOLD</div><h2 class="mt">Recovered evidence. New findings.</h2><p>The original recovery is still in the audit history. Additional blocking findings now exclude WO-1042 from trusted KPIs again. The historical 480-minute age is not a current completed duration.</p><a class="button lime" href="#studio/INC-1042">Inspect the new findings ${icon('arrow')}</a></article>`;
  return `<article class="hero"><div class="eyebrow">${recovered?'RECOVERY APPLIED · HISTORICAL COMPARISON':'CURRENT REPORTING GAP · WO-1042'}</div><h2 class="mt">${recovered?'Evidence restored. 720 units included.':'A missing event obscures completion.'}</h2><p>${recovered?'The approved record supports 190 minutes elapsed. The earlier 480-minute open-age estimate is historical and is not a current unresolved delay.':'480 minutes is the naive age at the scenario clock, not a valid completed duration. The order currently contributes no trusted units.'}</p><a class="button lime" href="#studio/INC-1042">Trace the reviewed evidence ${icon('arrow')}</a><p class="small">The operational investigation has its own status in <a href="#studio/INC-1043">INC-1043</a>.</p></article>`;
}

function stressPanel() {
  const s=app.data.lab.stress;
  const metric=x=>pct(x===null?null:x*100);
  return `<section class="card panel mt"><div class="card-head"><div><div class="eyebrow muted">STRESS PROTOCOL ${e(s.protocol)}</div><h2>Perfect on one seed is not enough.</h2></div>${badge(n(s.total_testing)+' future observations')}</div>
    <p class="small muted">Six additional conditions × five predeclared seeds (${s.seeds.join(', ')}). Each seed has 200 future observations. These are detector stress experiments, separate from the production-order dataset; they are not independent real-world validation.</p>
    <div class="callout mb">${e(s.chronology)} An injected delay label is simulation truth, not a verified operational cause. False alerts and missed deviations are expected when distributions overlap.</div>
    <div class="table-wrap"><table class="table"><caption>Fixed threshold and robust threshold 3.5 · all seeds pooled per condition</caption><thead><tr><th>Condition / positives</th><th>Method</th><th>Precision</th><th>Recall</th><th>False positives</th><th>Missed</th><th>False-positive rate</th><th>Unscored</th></tr></thead><tbody>${s.conditions.map(c=>[c.fixed,c.thresholds[1]].map((m,j)=>`<tr><td>${j?'':`<b>${e(c.name)}</b><br>${m.positives} / ${c.testing} positives`}</td><td>${j?'Median / MAD':'Wait > 60 min'}</td><td>${metric(m.precision)}</td><td>${metric(m.recall)}</td><td>${m.fp}</td><td>${m.fn}</td><td>${metric(m.false_positive_rate)}</td><td>${m.unavailable}</td></tr>`).join('')).join('')}</tbody></table></div>
    <details class="evidence-details"><summary>Threshold sensitivity · 2.5 / 3.5 / 4.5, without choosing a winner on test data</summary><div class="table-wrap"><table class="table compact"><thead><tr><th>Condition</th><th>Threshold</th><th>Precision</th><th>Recall</th><th>FP / FN</th><th>Unscored</th></tr></thead><tbody>${s.conditions.flatMap(c=>c.thresholds.map(m=>`<tr><td>${e(c.name)}</td><td>${m.threshold}</td><td>${metric(m.precision)}</td><td>${metric(m.recall)}</td><td>${m.fp} / ${m.fn}</td><td>${m.unavailable}</td></tr>`)).join('')}</tbody></table></div></details>
    <details class="evidence-details"><summary>Inspect actual false alerts and missed synthetic deviations</summary><p>One example per available error type and condition, selected by first occurrence; threshold 3.5. Reproduce with seed and zero-based future index.</p><div class="table-wrap"><table class="table compact"><thead><tr><th>Condition</th><th>Error</th><th>Seed / index</th><th>Wait</th><th>Score</th></tr></thead><tbody>${s.examples.map(x=>`<tr><td>${e(x.condition)}</td><td>${e(x.outcome.replaceAll('_',' '))}</td><td>${x.seed} / ${x.test_index}</td><td>${x.wait}</td><td>${x.score===999?'↑ zero-MAD sentinel':x.score}</td></tr>`).join('')}</tbody></table></div></details>
    <div class="grid-2 mt">${s.conditions.map(c=>`<div class="callout info"><b>${e(c.name)}</b><p>${e(c.description)}</p><small>${c.training_per_seed} training observations per seed. ${c.key==='small'?'Abstentions are not counted as successful detections or true negatives.':c.key==='zero'?'999 is a directional sentinel, never a calibrated score or confidence.':''}</small></div>`).join('')}</div>
  </section>`;
}
