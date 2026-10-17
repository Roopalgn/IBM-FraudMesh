import { validateAnalysis, deriveView, maxStep, caseExport } from './model.js';
import { loadAnalysis } from './api.js';

const $ = id => document.getElementById(id);
const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette = ['#8da9ff','#c5a1f3','#63cfc4'];
let data, fixture, step = 0, collaborative = true, selectedBank = null, selectedNode = null, selectedAlert = null;
let activeView = 'network', timer = null, zoom = 1, source = 'fixture', toastTimer, caseOnly = true;
let connectionController=null, requestEpoch=0;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const empty = (title, description) => `<div class="empty-state"><span>◇</span><strong>${esc(title)}</strong><p>${esc(description)}</p></div>`;
const colorFor = id => palette[Math.max(0,data.banks.findIndex(b => b.id === id)) % palette.length];

function stop() { clearInterval(timer); timer = null; }
function notify(message) {
  $('toast').textContent = message; $('toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
}
function setData(next, origin) {
  stop(); caseOnly=true; data = next; source = origin; step = maxStep(data); selectedBank = selectedNode = selectedAlert = null; zoom = 1; render();
}
function switchView(view, focus = false) {
  activeView = view;
  for (const name of ['network','evidence','privacy','audit']) {
    $(`view-${name}`).hidden = name !== view;
    $(`tab-${name}`).setAttribute('aria-selected', String(name === view));
    $(`tab-${name}`).tabIndex = name === view ? 0 : -1;
  }
  document.querySelectorAll('.rail-button[data-view]').forEach(b => b.classList.toggle('active',b.dataset.view === view));
  if (focus) $(`tab-${view}`).focus();
}
function render() {
  if (!data) return;
  const view = deriveView(data,step,collaborative);
  const available = view.alerts.find(a => a.id === selectedAlert) || view.alerts[0];
  selectedAlert = available?.id || null;
  $('result-context').textContent=source==='fixture'?'Authored outcomes; replay does not run a detector.':source==='snapshot'?`Saved computed output · backend ${data.provenance.backend_commit.slice(0,7)} · no live request or timing measurement.`:data.measurement?`Backend analysis: ${data.measurement.analysis_ms} ms. ${data.measurement.scope}`:'API snapshot; analysis timing unavailable.';
  const localCount = data.banks.reduce((n,b) => n + b.local_ring_count, 0);
  const summary = data.sharing_summary;
  $('source-badge').innerHTML = `<i></i>${source === 'fixture' ? 'Authored synthetic replay' : source === 'snapshot' ? 'Saved computed · synthetic' : 'API · synthetic data'}`;
  document.querySelector('.eyebrow').innerHTML = `COLLABORATIVE INTELLIGENCE <span>/</span> CASE ${esc(data.scenario_id)}`;
  $('disclosure').innerHTML = source === 'fixture'
    ? '<strong>A controlled scenario, not a production verdict.</strong> All entities and results below are synthetic fixtures.'
    : `<strong>Computed ${data.synthetic ? 'synthetic' : 'analysis'} outputs.</strong> Results and sharing claims have not been independently verified by this dashboard.`;
  document.querySelector('.environment small').textContent = `Confidential execution: ${summary.execution_verified?'unverified (backend flag only)':'unverified'}`;
  $('local-mode').classList.toggle('selected',!collaborative); $('collab-mode').classList.toggle('selected',collaborative);
  $('local-mode').setAttribute('aria-pressed',String(!collaborative)); $('collab-mode').setAttribute('aria-pressed',String(collaborative));
  $('replay-status').textContent = source === 'snapshot' ? 'Saved computed snapshot' : source !== 'fixture' ? 'Backend snapshot' : step === maxStep(data) ? 'Scenario complete' : `Event ${step} of ${maxStep(data)}`;
  $('play-button').textContent = timer ? 'Ⅱ Pause replay' : step === maxStep(data) ? '▶ Replay scenario' : '▶ Play scenario';
  for (const id of ['play-button','step-button','reset-button']) $(id).disabled = source !== 'fixture';
  $('step-button').disabled ||= step >= maxStep(data);
  const metrics = [
    ['Institutions connected',String(data.banks.length),'Three simulated bank processing stages','⌘',false],
    ['Visible relationships',String(view.edges.length),`${view.crossBankEdges.length} cross-bank ${collaborative ? 'links in view' : 'links visible'}`,'↗',false],
    ['Collaborative cases',String(view.alerts.length),collaborative ? available ? 'Review the evidence before any action' : source==='fixture'?'Waiting for complete relationship evidence':'No multi-bank case detected' : 'Switch to collaborative to inspect cases','◈',true],
    [collaborative ? summary.raw_rows_shared === null ? 'Raw-row traffic' : 'Raw rows shared' : 'Shared analysis',collaborative ? summary.raw_rows_shared === null ? 'Not audited' : String(summary.raw_rows_shared) : 'Off',collaborative ? source === 'fixture' ? 'Fixture contract · no raw transaction rows' : 'Backend-reported · not independently audited' : 'Local graph fragments only','◇',collaborative && summary.raw_rows_shared === 0]
  ];
  $('metrics').innerHTML = metrics.map(([title,value,note,symbol,accent]) => `<article class="metric"><div class="metric-top"><span>${esc(title)}</span><span class="metric-symbol">${symbol}</span></div><div class="metric-value ${accent?'accent':''}">${esc(value)}</div><div class="metric-note">${esc(note)}</div></article>`).join('');
  $('network-subtitle').textContent = collaborative ? 'Permitted relationship signals across participating institutions' : 'Institution-local links; cross-bank relationships are hidden';
  $('bank-legend').innerHTML = data.banks.map(b=>`<span><i class="legend-dot" style="background:${colorFor(b.id)}"></i>${esc(b.name)}</span>`).join('');
  $('graph-count').textContent = `${view.nodes.length} entity views / ${view.edges.length} links`;
  $('graph-legend-text').textContent = collaborative ? 'Cross-bank relationship' : 'Local relationship';
  $('graph-message').textContent = available ? `${available.id} · ${available.node_ids.length} linked entities · ${available.reasons.length} evidence types` : step === 0 ? 'Start the replay to reveal relationship signals.' : collaborative ? source==='fixture'?'Collecting relationship evidence…':'Analysis complete. No multi-bank case matched.' : 'Bank-local views. Shared entities are shown separately for each contributing bank.';
  const focusCase = collaborative && caseOnly && available;
  const graphView = focusCase ? {...view,nodes:view.nodes.filter(n=>available.node_ids.includes(n.id)),edges:view.edges.filter(e=>available.edge_ids.includes(e.id))} : view;
  $('graph-scope').disabled=!collaborative || !available;
  $('graph-scope').textContent=focusCase?'Show all signals':'Focus case';
  $('graph-count').textContent=`${graphView.nodes.length} entity views / ${graphView.edges.length} links${focusCase?' · case subgraph':''}`;
  renderGraph(graphView,available);
  renderCase(view,available);
  document.querySelector('.synthetic-label').textContent = data.synthetic ? 'SYNTHETIC' : 'BACKEND';
  document.querySelector('footer>span:last-child').textContent = `Decision support only · ${source==='fixture'?'Synthetic fixture results':'Backend-reported results'} · No production privacy guarantee`;
  renderEvidence(view,available);
  renderPrivacy();
  renderTrail(view);
  $('banks').innerHTML = data.banks.map(b => {
    const bankEdges = view.edges.filter(e => e.institution_id ? e.institution_id===b.id : view.nodeMap.get(e.source).bank_ids.includes(b.id) || view.nodeMap.get(e.target).bank_ids.includes(b.id));
    const active = bankEdges.length > 0;
    return `<button class="bank-card ${selectedBank===b.id?'selected':''}" data-bank="${esc(b.id)}" aria-pressed="${selectedBank===b.id}"><div class="bank-card-heading"><div class="bank-name"><span class="bank-icon" style="color:${colorFor(b.id)}">${esc(b.name.replace('Bank ',''))}</span>${esc(b.name)}</div><span class="local-badge">${source==='fixture'?'Simulated institution':'Backend output'}</span></div><div class="bank-stats"><div><strong>${b.entity_count}</strong>Entities in scenario</div><div><strong>${active?b.local_alerts:0}</strong>Local flags</div><div><strong>${active?b.local_ring_count:0}</strong>Local patterns</div></div><div class="bank-bottom"><span>◇</span>${selectedBank===b.id?'Focused · select again to clear':'Focus institution entities →'}</div></button>`;
  }).join('');
  const ringCount = step === maxStep(data) ? data.collaborative_alerts.length : view.alerts.length;
  const transactionFlags=data.banks.reduce((sum,b)=>sum+b.local_alerts,0);
  const combinedPatterns=data.comparison?.combined_patterns ?? null;
  $('comparison').innerHTML=[['Transaction-risk flags',transactionFlags],['Local structural patterns',localCount],['Combined structural patterns',combinedPatterns],['Multi-bank cases',ringCount]].map(([label,value])=>`<div class="result-unit"><span>${label}</span><strong>${value===null?'Unavailable':value}</strong></div>`).join('')+'<small>Different units and scopes; not an accuracy improvement.</small>';
  document.querySelector('.comparison-panel h2').textContent='Understand the result, not an uplift ratio.';
  $('comparison-description').textContent='Transaction flags, local structures, combined structures and multi-bank cases are distinct outputs. The shared team example includes a local payroll fan-out false positive.';
  switchView(activeView);
}

function renderGraph(view,alert) {
  const svg = $('graph');
  const fixed = [[180,120],[180,275],[440,320],[700,275],[700,120],[440,65]];
  const positions = new Map(view.nodes.map((n,i) => {
    const theta = -Math.PI/2 + i * Math.PI*2/view.nodes.length;
    return [n.id,view.nodes.length === 6 ? fixed[i] : [440+290*Math.cos(theta),200+145*Math.sin(theta)]];
  }));
  const alertEdges = new Set(alert?.edge_ids || []);
  let html = `<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="27" refY="3.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L7 3.5L0 7" fill="#b9f077"/></marker><marker id="local-arrow" markerWidth="7" markerHeight="7" refX="27" refY="3.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L7 3.5L0 7" fill="#73849a"/></marker></defs><g transform="translate(440 200) scale(${zoom}) translate(-440 -200)"><ellipse cx="440" cy="200" rx="265" ry="135" fill="none" stroke="#2b3543" stroke-dasharray="3 8"/><ellipse cx="440" cy="200" rx="195" ry="95" fill="none" stroke="#212d3a"/>`;
  for (const edge of view.edges) {
    const [x1,y1] = positions.get(edge.source), [x2,y2] = positions.get(edge.target);
    const cross = collaborative && (edge.institution_id ? [edge.source,edge.target].some(id=>view.nodeMap.get(id).bank_ids.length>1) : view.nodeMap.get(edge.source).bank_id !== view.nodeMap.get(edge.target).bank_id);
    const highlighted = alertEdges.has(edge.id);
    const dimmed = selectedBank && (edge.institution_id ? edge.institution_id!==selectedBank : ![...view.nodeMap.get(edge.source).bank_ids,...view.nodeMap.get(edge.target).bank_ids].includes(selectedBank));
    html += `<path d="M${x1} ${y1}L${x2} ${y2}" fill="none" stroke="${highlighted?'#b9f077':cross?'#8aa775':'#73849a'}" stroke-width="${highlighted?2:1.4}" ${cross?'stroke-dasharray="6 5"':''} opacity="${dimmed?.2:.85}" marker-end="url(#${highlighted||cross?'arrow':'local-arrow'})"><title>${esc(edge.id)}: ${esc(edge.source)} → ${esc(edge.target)} · ${esc(edge.time_bucket)}</title></path>`;
  }
  html += `<text x="440" y="186" text-anchor="middle" fill="${alert?'#b9f077':'#6f8196'}" font-family="Consolas,monospace" font-size="10" letter-spacing="2">${collaborative?'SHARED INTELLIGENCE':'LOCAL VISIBILITY'}</text><text x="440" y="213" text-anchor="middle" fill="#cad4e2" font-size="18">${alert?'A connected case':collaborative?(source==='fixture'?'Building the picture':'No multi-bank case'):'Bank-local views'}</text><text x="440" y="235" text-anchor="middle" fill="#8091a7" font-size="10">${alert?`${alert.node_ids.length} pseudonymous entities`:'Select an entity to inspect local risk'}</text>`;
  for (const node of view.nodes) {
    const [x,y] = positions.get(node.id), color = node.bank_ids.length>1?'#b6cbaf':colorFor(node.bank_id);
    const active = view.edges.some(e => e.source===node.id || e.target===node.id);
    const dimmed = selectedBank && !node.bank_ids.includes(selectedBank);
    const selected = selectedNode===node.id;
    const bank = data.banks.find(b=>b.id===node.bank_id);
    const memberships = node.bank_ids.map(id=>data.banks.find(b=>b.id===id).name).join(' / ');
    html += `<g class="node" data-node="${esc(node.id)}" role="button" tabindex="0" aria-label="Inspect ${esc(node.label)}, ${esc(bank.name)}, maximum incident transaction score ${node.local_risk.toFixed(2)} (uncalibrated)" opacity="${dimmed?.25:active?1:.45}"><circle cx="${x}" cy="${y}" r="${selected?30:27}" fill="${color}" fill-opacity=".07" stroke="${selected?'#b9f077':color}" stroke-opacity=".3"/><circle cx="${x}" cy="${y}" r="20" fill="#1e2938" stroke="${color}" stroke-width="1.5"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="${color}" font-size="12">${node.bank_ids.length>1?node.bank_ids.length+'B':esc(bank.name.replace('Bank ',''))}</text><text x="${x}" y="${y+45}" text-anchor="middle" fill="#d6dfed" font-size="11">${esc(node.label)}</text><text x="${x}" y="${y+61}" text-anchor="middle" fill="#788a9f" font-size="9">${esc(memberships)} · ${node.local_risk.toFixed(2)} max incident score</text></g>`;
  }
  svg.innerHTML = html + '</g>';
  $('zoom-reset').textContent = `${Math.round(zoom*100)}%`;
}
function renderCase(view,alert) {
  $('case-title').textContent = alert?.title || (collaborative ? source==='fixture'?'Awaiting a connected case':'No multi-bank case detected' : 'Local-only perspective');
  $('case-badge').textContent = alert ? 'Review' : 'Observe'; $('case-badge').className = `badge ${alert?'danger':'neutral'}`;
  const node = view.nodeMap.get(selectedNode);
  let html = `<div class="case-body"><p class="case-intro">${alert ? 'Related signals form a coordinated pattern across institutional boundaries. This is a case for investigation, not a confirmed fraud verdict.' : collaborative ? 'Inspect the visible relationships. A case requires supporting evidence; no case does not establish that all activity is legitimate.' : 'These are separate bank-visible relationship views. Local structural findings are reported in the institution cards.'}</p>`;
  if (view.alerts.length > 1) html += `<label for="alert-select" class="case-section-title">SELECT CASE</label><select id="alert-select">${view.alerts.map(a=>`<option value="${esc(a.id)}" ${a.id===alert.id?'selected':''}>${esc(a.id)} · ${esc(a.title)}</option>`).join('')}</select>`;
  html += `<div class="case-score"><span>${alert?'RELATIONSHIP EVIDENCE':'VISIBLE LOCAL FRAGMENTS'}</span><strong>${alert?alert.edge_ids.length:view.edges.length} <span>links</span></strong></div>`;
  if (node) html += `<div class="selected-entity"><strong>${esc(node.label)}</strong> · ${esc(data.banks.find(b=>b.id===node.bank_id).name)}<code class="entity-token">${esc(node.id)}</code><p>Contributing memberships: ${node.bank_ids.map(id=>esc(data.banks.find(b=>b.id===id).name)).join(', ')}. These are signal memberships, not ownership.</p><br>Maximum incident transaction score: ${node.local_risk.toFixed(2)} <span class="muted">(${source==='fixture'?'fixture score':'backend score'}; uncalibrated score, not a fraud probability)</span></div>`;
  const bank = data.banks.find(b=>b.id===selectedBank);
  if (bank) html += `<div class="selected-entity"><strong>${esc(bank.name)} · local findings</strong>${bank.local_findings.length ? bank.local_findings.map(f=>`<p><strong>${esc(f.title)}</strong>${esc(f.detail)}</p>`).join('') : '<p>No local finding details supplied by the backend.</p>'}<small>Complete-scenario findings · not a replay timestamp</small></div>`;
  html += `<div class="case-section-title">${alert?'WHY THIS WAS FLAGGED':'WHAT TO LOOK FOR'}</div>`;
  const reasons = alert?.reasons || (source!=='fixture' ? [{title:'Snapshot analysis complete',detail:'The backend reported no multi-bank case in this view. Inspect institution findings and the permitted sharing boundary.'}] : [{title:'Institution-local links',detail:'Inspect each bank’s fragment, then enable collaborative analysis to connect the path.'},{title:'Wait for the final relationship',detail:'The complete synthetic cycle is revealed at event six.'}]);
  html += reasons.map((r,i)=>`<div class="reason"><span class="reason-number">${String(i+1).padStart(2,'0')}</span><div><strong>${esc(r.title)}</strong><p>${esc(r.detail)}</p></div></div>`).join('');
  html += `<div class="case-footnote">${source==='fixture'?'Pre-authored synthetic replay.':source==='snapshot'?'Saved computed synthetic output; not a live API result.':'API-computed synthetic output.'} Pseudonyms and graph relationships can remain sensitive.</div><button class="button subtle" data-view="${alert?'evidence':'privacy'}">${alert?'Inspect supporting evidence':'Inspect sharing boundary'} ↗</button></div>`;
  $('case-content').innerHTML = html;
}
function renderEvidence(view,alert) {
  const refs=new Set(alert?.edge_ids||[]);
  $('view-evidence').innerHTML='<h3>Relationship evidence</h3><p>Highlighted rows support the selected case. A contributor supplies a signal; it does not exclusively own both endpoints. Signal scores are uncalibrated, and hour buckets are not detection latency.</p>'+(view.edges.length?`<table class="evidence-table"><thead><tr><th scope="col">SIGNAL</th><th scope="col">PATH</th><th scope="col">CONTRIBUTOR</th><th scope="col">HOUR</th><th scope="col">SIGNAL SCORE</th></tr></thead><tbody>${view.edges.map(e=>`<tr class="${refs.has(e.id)?'supporting-evidence':''}"><td class="mono">${esc(e.id)}</td><td><button class="entity-button" data-node="${esc(e.source)}">${esc(view.nodeMap.get(e.source).label)}</button> → <button class="entity-button" data-node="${esc(e.target)}">${esc(view.nodeMap.get(e.target).label)}</button></td><td>${esc(data.banks.find(b=>b.id===e.institution_id)?.name||'Fixture relationship')}</td><td>${esc(e.time_bucket)}</td><td>${e.local_risk_score===undefined?'Unavailable':e.local_risk_score.toFixed(2)}</td></tr>`).join('')}</tbody></table>`:empty('No visible relationships',source==='fixture'?'Use Step to reveal authored signals.':'The analysis returned no relationships in this view.'));
}
function renderPrivacy() {
  const s = data.sharing_summary;
  $('view-privacy').innerHTML = `<h3>A visible, limited sharing boundary</h3><p>${source==='fixture'?'The bundled fixture contains only pseudonymous graph display data. The browser does not contain simulated raw banking records.':'This panel describes the backend’s reported sharing policy; it does not independently audit bank-side traffic.'}</p><div class="privacy-columns"><div class="privacy-card local"><h3>01 / Retained at each bank</h3><ul>${s.retained_local.map(f=>`<li>${esc(f)}</li>`).join('')}</ul></div><div class="privacy-card"><h3>02 / Relationship fields</h3><ul>${s.shared_fields.map(f=>`<li><code>${esc(f)}</code></li>`).join('')}</ul></div></div><div class="boundary-note"><strong>${s.raw_rows_shared===null?'Raw-row traffic is not independently audited':`${s.raw_rows_shared} raw transaction rows shared`}</strong> · ${source==='fixture'?'fixture declaration, not a measured production result':'backend-reported value'}. Institution ID, pseudonymous entity IDs and local risk are also returned for display.</div><div class="case-section-title">SECURITY STATUS & LIMITS</div><p>Confidential execution: <strong>${s.execution_verified?'unverified (backend flag is not attestation)':'unverified'}</strong>. Pseudonymization is not anonymity. Relationships, risk bands and timing buckets can expose patterns. Authentication, authorization, key management, retention controls and deployment attestation belong to the integrated system.</p><p>The local-only toggle is a visual comparison. It is not an access-control boundary; this browser receives the whole analysis response. Replay history is an in-memory presentation trail, not a tamper-evident backend audit log.</p>`;
  if(s.validation_scope)$('view-privacy').innerHTML+=`<p>Service validation scope: ${esc(s.validation_scope)}</p>`;
  if(data.score_semantics)$('view-privacy').innerHTML+=`<p>Score semantics: ${esc(data.score_semantics)}</p>`;
}
function renderTrail(view) {
  $('view-audit').innerHTML = `<h3>${source==='fixture'?'Synthetic replay trail':source==='snapshot'?'Saved computed relationships':'Backend snapshot relationships'}</h3><p>${source==='fixture'?'A deterministic presentation of the bundled fixture. These are scenario time buckets, not system logs.':'Relationships from the returned analysis. This panel is not a persisted or verified audit log.'}</p><div class="trail-row"><span>INIT</span><div><strong>${data.banks.length} institutions in the scenario</strong><p>${collaborative?'Collaborative relationship view enabled.':'Local view enabled; cross-bank relationships hidden.'}</p></div></div>${view.edges.map(e=>`<div class="trail-row"><span>${esc(e.time_bucket)}</span><div><strong>${esc(e.source)} → ${esc(e.target)}</strong><p>${esc(e.id)} · ${esc(e.kind)} · ${esc(e.risk_band)} risk band</p></div></div>`).join('')}${view.alerts.map(a=>`<div class="trail-row"><span>CASE</span><div><strong>${esc(a.id)} · ${esc(a.title)}</strong><p>${a.edge_ids.length} supporting links; ${a.reasons.length} reason codes. Investigator review required.</p></div></div>`).join('')}`;
}

document.addEventListener('click',event=>{
  const viewButton=event.target.closest('[data-view]');
  if(viewButton) switchView(viewButton.dataset.view);
  const entity=event.target.closest('[data-node]');
  if(entity && data) { selectedNode = selectedNode===entity.dataset.node?null:entity.dataset.node; render(); }
  const bank=event.target.closest('[data-bank]');
  if(bank && data) {selectedBank=selectedBank===bank.dataset.bank?null:bank.dataset.bank; render();}
});
$('graph').addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.closest('[data-node]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true})); const id=selectedNode; if(id) Array.from($('graph').querySelectorAll('[data-node]')).find(n=>n.dataset.node===id)?.focus();}});
document.querySelector('.tabbar').addEventListener('keydown',e=>{
  if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;
  e.preventDefault();const names=['network','evidence','privacy','audit'];let i=names.indexOf(activeView);
  i=e.key==='Home'?0:e.key==='End'?3:(i+(e.key==='ArrowRight'?1:3))%4;switchView(names[i],true);
});
$('graph-scope').onclick=()=>{caseOnly=!caseOnly;render();};
$('local-mode').onclick=()=>{collaborative=false;render();}; $('collab-mode').onclick=()=>{collaborative=true;render();};
$('reset-button').onclick=()=>{stop();step=0;selectedNode=selectedBank=null;render();notify('Scenario reset. Use Step or Play to begin.');};
$('step-button').onclick=()=>{stop();step=Math.min(step+1,maxStep(data));render();};
$('play-button').onclick=()=>{
  if(timer){stop();render();return;}
  if(step>=maxStep(data))step=0;
  timer=setInterval(()=>{step=Math.min(step+1,maxStep(data));if(step>=maxStep(data))stop();render();},reducedMotion?2200:1500);render();
};
for(const [id,delta] of [['zoom-in',.15],['zoom-out',-.15],['zoom-reset',0]])$(id).onclick=()=>{zoom=delta?Math.max(.7,Math.min(1.6,zoom+delta)):1;render();};
$('case-content').addEventListener('change',e=>{if(e.target.id==='alert-select'){selectedAlert=e.target.value;render();}});
$('export-button').onclick=()=>{
  if(!data)return;
  const blob=new Blob([JSON.stringify(caseExport(data,step,collaborative,source),null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`fraudmesh-case-${collaborative?'collaborative':'local'}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Case exported as JSON with source and scope labels.');
};
$('run-analysis').onclick=()=>{$('connection-form').requestSubmit();};
$('settings-open').onclick=()=>{$('settings-dialog').showModal();};
$('settings-close').onclick=()=>{connectionController?.abort();$('settings-dialog').close();};
$('settings-dialog').addEventListener('cancel',()=>connectionController?.abort());
$('mock-button').onclick=()=>{requestEpoch++;connectionController?.abort();$('connect-button').disabled=$('run-analysis').disabled=false;if(fixture){setData(structuredClone(fixture),'fixture');$('connection-status').textContent='';$('settings-dialog').close();notify('Restored the synthetic fixture.');}};
$('connection-form').onsubmit=async e=>{
  e.preventDefault();const epoch=++requestEpoch;connectionController?.abort();const controller=new AbortController();connectionController=controller;
  $('connect-button').disabled=$('run-analysis').disabled=true;$('connection-form').setAttribute('aria-busy','true');stop();render();
  try{
    const next=await loadAnalysis($('api-url').value,$('scenario-select').value,{signal:controller.signal,onProgress:message=>{$('connection-status').textContent=message;}});
    if(epoch!==requestEpoch||controller.signal.aborted)return;
    setData(next,'api');$('settings-dialog').close();$('connection-status').textContent='';notify('Computed API snapshot loaded; replay disabled.');
  }catch(error){if(epoch===requestEpoch&&!controller.signal.aborted){$('connection-status').textContent=`Connection failed: ${error.message} Previous data remains visible. No fallback was loaded.`;if(!$('settings-dialog').open)$('settings-dialog').showModal();}}
  finally{if(epoch===requestEpoch){$('connect-button').disabled=$('run-analysis').disabled=false;$('connection-form').removeAttribute('aria-busy');}}
};
$('load-snapshot').onclick=async()=>{
  const epoch=++requestEpoch;connectionController?.abort();$('connect-button').disabled=$('run-analysis').disabled=false;
  try{const response=await fetch(`./public/computed/${$('scenario-select').value}.json`);if(!response.ok)throw new Error(`HTTP ${response.status}`);const saved=await response.json();const next=validateAnalysis(saved.analysis);
    if(epoch!==requestEpoch)return;
    if(saved.provenance?.kind!=='saved-computed-synthetic'||!/^[0-9a-f]{40}$/.test(saved.provenance.backend_commit)||saved.provenance.scenario!==$('scenario-select').value||next.synthetic!==true)throw new Error('Saved example provenance is missing or mismatched.');
    next.provenance=saved.provenance;setData(next,'snapshot');notify('Saved computed synthetic example loaded. No API request was made.');
  }catch(error){if(epoch===requestEpoch)notify(`Saved example unavailable: ${error.message}. Existing data retained.`);}
};

try {
  const response=await fetch('./public/scenario.json');if(!response.ok)throw new Error(`Fixture HTTP ${response.status}`);
  fixture=validateAnalysis(await response.json());setData(structuredClone(fixture),'fixture');
} catch(error) {
  $('metrics').innerHTML=empty('Unable to load the demo',error.message+' Serve this folder over HTTP; see README.md.');
  $('play-button').disabled=$('step-button').disabled=$('reset-button').disabled=true;
  $('connection-status').textContent='The bundled fixture could not load. You can still connect to a compatible API.';
}

// The unified Python server supplies the UI and API from the same origin.
try {
 const health = await fetch('/health',{signal:AbortSignal.timeout(2000)});
 if(health.ok && (await health.json()).application==='FraudMesh'){
  $('api-url').value=location.origin;
  $('connection-form').requestSubmit();
 }
} catch {}
