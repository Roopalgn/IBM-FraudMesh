import { validateAnalysis, deriveView, maxStep, caseExport } from './model.js';

const $ = id => document.getElementById(id);
const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette = ['#8da9ff','#c5a1f3','#63cfc4'];
let data, fixture, step = 0, collaborative = true, selectedBank = null, selectedNode = null, selectedAlert = null;
let activeView = 'network', timer = null, zoom = 1, source = 'fixture', toastTimer;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const empty = (title, description) => `<div class="empty-state"><span>◇</span><strong>${esc(title)}</strong><p>${esc(description)}</p></div>`;
const colorFor = id => palette[Math.max(0,data.banks.findIndex(b => b.id === id)) % palette.length];

function stop() { clearInterval(timer); timer = null; }
function notify(message) {
  $('toast').textContent = message; $('toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
}
function setData(next, origin) {
  stop(); data = next; source = origin; step = maxStep(data); selectedBank = selectedNode = selectedAlert = null; zoom = 1; render();
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
  const localCount = data.banks.reduce((n,b) => n + b.local_ring_count, 0);
  const summary = data.sharing_summary;
  $('source-badge').innerHTML = `<i></i>${source === 'fixture' ? 'Synthetic demo' : data.synthetic ? 'API · synthetic data' : 'API · backend output'}`;
  document.querySelector('.eyebrow').innerHTML = `COLLABORATIVE INTELLIGENCE <span>/</span> CASE ${esc(data.scenario_id)}`;
  $('disclosure').innerHTML = source === 'fixture'
    ? '<strong>A controlled scenario, not a production verdict.</strong> All entities and results below are synthetic fixtures.'
    : `<strong>Backend-reported ${data.synthetic ? 'synthetic' : 'analysis'} outputs.</strong> Results and sharing claims have not been independently verified by this dashboard.`;
  document.querySelector('.environment small').textContent = `Confidential execution: ${source === 'fixture' ? 'unverified' : summary.execution_verified ? 'backend reports verified' : 'unverified'}`;
  $('local-mode').classList.toggle('selected',!collaborative); $('collab-mode').classList.toggle('selected',collaborative);
  $('local-mode').setAttribute('aria-pressed',String(!collaborative)); $('collab-mode').setAttribute('aria-pressed',String(collaborative));
  $('replay-status').textContent = source !== 'fixture' ? 'Backend snapshot' : step === maxStep(data) ? 'Scenario complete' : `Event ${step} of ${maxStep(data)}`;
  $('play-button').textContent = timer ? 'Ⅱ Pause replay' : step === maxStep(data) ? '▶ Replay scenario' : '▶ Play scenario';
  for (const id of ['play-button','step-button','reset-button']) $(id).disabled = source !== 'fixture';
  $('step-button').disabled ||= step >= maxStep(data);
  const metrics = [
    ['Institutions connected',String(data.banks.length),'Independent institutional data boundaries','⌘',false],
    ['Visible relationships',String(view.edges.length),`${view.crossBankEdges.length} cross-bank ${collaborative ? 'links in view' : 'links visible'}`,'↗',false],
    ['Collaborative cases',String(view.alerts.length),collaborative ? available ? 'Review the evidence before any action' : 'Waiting for complete relationship evidence' : 'Switch to collaborative to inspect cases','◈',true],
    [collaborative ? 'Raw rows shared' : 'Shared analysis',collaborative ? String(summary.raw_rows_shared) : 'Off',collaborative ? source === 'fixture' ? 'Fixture contract · no raw transaction rows' : 'Backend-reported · not independently audited' : 'Local graph fragments only','◇',collaborative && summary.raw_rows_shared === 0]
  ];
  $('metrics').innerHTML = metrics.map(([title,value,note,symbol,accent]) => `<article class="metric"><div class="metric-top"><span>${esc(title)}</span><span class="metric-symbol">${symbol}</span></div><div class="metric-value ${accent?'accent':''}">${esc(value)}</div><div class="metric-note">${esc(note)}</div></article>`).join('');
  $('network-subtitle').textContent = collaborative ? 'Permitted relationship signals across participating institutions' : 'Institution-local links; cross-bank relationships are hidden';
  $('bank-legend').innerHTML = data.banks.map(b=>`<span><i class="legend-dot" style="background:${colorFor(b.id)}"></i>${esc(b.name)}</span>`).join('');
  $('graph-count').textContent = `${data.graph.nodes.length} entities / ${view.edges.length} links`;
  $('graph-legend-text').textContent = collaborative ? 'Cross-bank relationship' : 'Local relationship';
  $('graph-message').textContent = available ? `${available.id} · ${available.node_ids.length} linked entities · ${available.reasons.length} evidence types` : step === 0 ? 'Start the replay to reveal relationship signals.' : collaborative ? 'Collecting relationship evidence…' : 'Disconnected fragments. Cross-bank links are outside each local view.';
  renderGraph(view,available);
  renderCase(view,available);
  document.querySelector('.synthetic-label').textContent = data.synthetic ? 'SYNTHETIC' : 'BACKEND';
  document.querySelector('footer>span:last-child').textContent = `Decision support only · ${source==='fixture'?'Synthetic fixture results':'Backend-reported results'} · No production privacy guarantee`;
  renderEvidence(view);
  renderPrivacy();
  renderTrail(view);
  $('banks').innerHTML = data.banks.map(b => {
    const bankEdges = view.edges.filter(e => view.nodeMap.get(e.source).bank_id === b.id || view.nodeMap.get(e.target).bank_id === b.id);
    const active = bankEdges.length > 0;
    return `<button class="bank-card ${selectedBank===b.id?'selected':''}" data-bank="${esc(b.id)}" aria-pressed="${selectedBank===b.id}"><div class="bank-card-heading"><div class="bank-name"><span class="bank-icon" style="color:${colorFor(b.id)}">${esc(b.id)}</span>${esc(b.name)}</div><span class="local-badge">${source==='fixture'?'Simulated institution':'Backend output'}</span></div><div class="bank-stats"><div><strong>${b.entity_count}</strong>Entities in scenario</div><div><strong>${active?b.local_alerts:0}</strong>Local flags</div><div><strong>${active?b.local_ring_count:0}</strong>Local rings</div></div><div class="bank-bottom"><span>◇</span>${selectedBank===b.id?'Focused · select again to clear':'Focus institution entities →'}</div></button>`;
  }).join('');
  const ringCount = step === maxStep(data) ? data.collaborative_alerts.length : view.alerts.length;
  const denominator = Math.max(1,localCount,ringCount);
  $('comparison').innerHTML = `<div class="bar-row"><span>Local rings</span><div class="bar-track"><div class="bar-fill local" style="width:${100*localCount/denominator}%"></div></div><strong>${localCount}</strong></div><div class="bar-row"><span>Shared cases</span><div class="bar-track"><div class="bar-fill" style="width:${100*ringCount/denominator}%"></div></div><strong>${ringCount}</strong></div><small>${source==='fixture'?'Fixture counts':'Backend-reported counts'} · ${step===maxStep(data)?'complete scenario':'current replay step'} · not a general accuracy benchmark</small>`;
  $('comparison-description').textContent = source === 'fixture' ? 'Each bank sees a local fragment. Permitted relationship signals reveal the complete cycle.' : 'Compare backend-reported local ring counts with collaborative cases. These counts do not establish model accuracy.';
  switchView(activeView);
}

function renderGraph(view,alert) {
  const svg = $('graph');
  const fixed = [[180,120],[180,275],[440,320],[700,275],[700,120],[440,65]];
  const positions = new Map(data.graph.nodes.map((n,i) => {
    const theta = -Math.PI/2 + i * Math.PI*2/data.graph.nodes.length;
    return [n.id,data.graph.nodes.length === 6 ? fixed[i] : [440+290*Math.cos(theta),200+145*Math.sin(theta)]];
  }));
  const alertEdges = new Set(alert?.edge_ids || []);
  let html = `<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="27" refY="3.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L7 3.5L0 7" fill="#b9f077"/></marker><marker id="local-arrow" markerWidth="7" markerHeight="7" refX="27" refY="3.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L7 3.5L0 7" fill="#73849a"/></marker></defs><g transform="translate(440 200) scale(${zoom}) translate(-440 -200)"><ellipse cx="440" cy="200" rx="265" ry="135" fill="none" stroke="#2b3543" stroke-dasharray="3 8"/><ellipse cx="440" cy="200" rx="195" ry="95" fill="none" stroke="#212d3a"/>`;
  for (const edge of view.edges) {
    const [x1,y1] = positions.get(edge.source), [x2,y2] = positions.get(edge.target);
    const cross = view.nodeMap.get(edge.source).bank_id !== view.nodeMap.get(edge.target).bank_id;
    const highlighted = alertEdges.has(edge.id);
    const dimmed = selectedBank && ![view.nodeMap.get(edge.source).bank_id,view.nodeMap.get(edge.target).bank_id].includes(selectedBank);
    html += `<path d="M${x1} ${y1}L${x2} ${y2}" fill="none" stroke="${highlighted?'#b9f077':cross?'#8aa775':'#73849a'}" stroke-width="${highlighted?2:1.4}" ${cross?'stroke-dasharray="6 5"':''} opacity="${dimmed?.2:.85}" marker-end="url(#${highlighted||cross?'arrow':'local-arrow'})"><title>${esc(edge.id)}: ${esc(edge.source)} → ${esc(edge.target)} · ${esc(edge.time_bucket)}</title></path>`;
  }
  html += `<text x="440" y="186" text-anchor="middle" fill="${alert?'#b9f077':'#6f8196'}" font-family="Consolas,monospace" font-size="10" letter-spacing="2">${collaborative?'SHARED INTELLIGENCE':'LOCAL VISIBILITY'}</text><text x="440" y="213" text-anchor="middle" fill="#cad4e2" font-size="18">${alert?'A connected case':collaborative?'Building the picture':'Three separate fragments'}</text><text x="440" y="235" text-anchor="middle" fill="#8091a7" font-size="10">${alert?`${alert.node_ids.length} pseudonymous entities`:'Select an entity to inspect local risk'}</text>`;
  for (const node of data.graph.nodes) {
    const [x,y] = positions.get(node.id), color = colorFor(node.bank_id);
    const active = view.edges.some(e => e.source===node.id || e.target===node.id);
    const dimmed = selectedBank && selectedBank !== node.bank_id;
    const selected = selectedNode===node.id;
    const bank = data.banks.find(b=>b.id===node.bank_id);
    html += `<g class="node" data-node="${esc(node.id)}" role="button" tabindex="0" aria-label="Inspect ${esc(node.label)}, ${esc(bank.name)}, local risk ${Math.round(node.local_risk*100)} percent" opacity="${dimmed?.25:active?1:.45}"><circle cx="${x}" cy="${y}" r="${selected?30:27}" fill="${color}" fill-opacity=".07" stroke="${selected?'#b9f077':color}" stroke-opacity=".3"/><circle cx="${x}" cy="${y}" r="20" fill="#1e2938" stroke="${color}" stroke-width="1.5"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="${color}" font-size="12">${esc(node.bank_id)}</text><text x="${x}" y="${y+45}" text-anchor="middle" fill="#d6dfed" font-size="11">${esc(node.label)}</text><text x="${x}" y="${y+61}" text-anchor="middle" fill="#788a9f" font-size="9">${esc(bank.name)} · ${Math.round(node.local_risk*100)}% local risk</text></g>`;
  }
  svg.innerHTML = html + '</g>';
  $('zoom-reset').textContent = `${Math.round(zoom*100)}%`;
}
function renderCase(view,alert) {
  $('case-title').textContent = alert?.title || (collaborative ? 'Awaiting a connected case' : 'Local-only perspective');
  $('case-badge').textContent = alert ? 'Review' : 'Observe'; $('case-badge').className = `badge ${alert?'danger':'neutral'}`;
  const node = data.graph.nodes.find(n=>n.id===selectedNode);
  let html = `<div class="case-body"><p class="case-intro">${alert ? 'Related signals form a coordinated pattern across institutional boundaries. This is a case for investigation, not a confirmed fraud verdict.' : collaborative ? 'As relationships arrive, the shared graph becomes visible. A case appears only when its supporting evidence is available.' : 'Each institution has a partial view. Local flags alone do not reconstruct the cross-bank cycle in this scenario.'}</p>`;
  if (view.alerts.length > 1) html += `<label for="alert-select" class="case-section-title">SELECT CASE</label><select id="alert-select">${view.alerts.map(a=>`<option value="${esc(a.id)}" ${a.id===alert.id?'selected':''}>${esc(a.id)} · ${esc(a.title)}</option>`).join('')}</select>`;
  html += `<div class="case-score"><span>${alert?'RELATIONSHIP EVIDENCE':'VISIBLE LOCAL FRAGMENTS'}</span><strong>${alert?alert.edge_ids.length:view.edges.length} <span>links</span></strong></div>`;
  if (node) html += `<div class="selected-entity"><strong>${esc(node.label)}</strong> · ${esc(data.banks.find(b=>b.id===node.bank_id).name)}<br>Local risk: ${Math.round(node.local_risk*100)}% <span class="muted">(${source==='fixture'?'fixture score':'backend score'}; not a fraud verdict)</span></div>`;
  const bank = data.banks.find(b=>b.id===selectedBank);
  if (bank) html += `<div class="selected-entity"><strong>${esc(bank.name)} · local findings</strong>${bank.local_findings.length ? bank.local_findings.map(f=>`<p><strong>${esc(f.title)}</strong>${esc(f.detail)}</p>`).join('') : '<p>No local finding details supplied by the backend.</p>'}<small>Complete-scenario findings · not a replay timestamp</small></div>`;
  html += `<div class="case-section-title">${alert?'WHY THIS WAS FLAGGED':'WHAT TO LOOK FOR'}</div>`;
  const reasons = alert?.reasons || [{title:'Institution-local links',detail:'Inspect each bank’s fragment, then enable collaborative analysis to connect the path.'},{title:'Wait for the final relationship',detail:'The complete synthetic cycle is revealed at event six.'}];
  html += reasons.map((r,i)=>`<div class="reason"><span class="reason-number">${String(i+1).padStart(2,'0')}</span><div><strong>${esc(r.title)}</strong><p>${esc(r.detail)}</p></div></div>`).join('');
  html += `<div class="case-footnote">${source==='fixture'?'Synthetic fixture, pre-authored outcomes. No model is running in this dashboard.':'Backend results shown as received. The frontend does not run a detector.'} Pseudonyms and graph relationships can remain sensitive.</div><button class="button subtle" data-view="${alert?'evidence':'privacy'}">${alert?'Inspect supporting evidence':'Inspect sharing boundary'} ↗</button></div>`;
  $('case-content').innerHTML = html;
}
function renderEvidence(view) {
  $('view-evidence').innerHTML = `<h3>Relationship evidence</h3><p>${collaborative?'Permitted graph signals in the current view.':'Only links between entities in the same institution are shown.'} Event times are coarse buckets; no exact amount is present.</p>` + (view.edges.length ? `<table class="evidence-table"><thead><tr><th scope="col">RELATIONSHIP</th><th scope="col">PATH</th><th scope="col">BUCKET</th><th scope="col">RISK</th></tr></thead><tbody>${view.edges.map(e=>`<tr><td class="mono">${esc(e.id)}</td><td><button class="entity-button" data-node="${esc(e.source)}">${esc(e.source)}</button><span class="muted"> → </span><button class="entity-button" data-node="${esc(e.target)}">${esc(e.target)}</button></td><td class="mono">${esc(e.time_bucket)}</td><td>${esc(e.risk_band)}</td></tr>`).join('')}</tbody></table>` : empty('No relationship evidence yet','Use Step or Play scenario to reveal the synthetic signals.'));
}
function renderPrivacy() {
  const s = data.sharing_summary;
  $('view-privacy').innerHTML = `<h3>A visible, limited sharing boundary</h3><p>${source==='fixture'?'The bundled fixture contains only pseudonymous graph display data. The browser does not contain simulated raw banking records.':'This panel describes the backend’s reported sharing policy; it does not independently audit bank-side traffic.'}</p><div class="privacy-columns"><div class="privacy-card local"><h3>01 / Retained at each bank</h3><ul>${s.retained_local.map(f=>`<li>${esc(f)}</li>`).join('')}</ul></div><div class="privacy-card"><h3>02 / Relationship fields</h3><ul>${s.shared_fields.map(f=>`<li><code>${esc(f)}</code></li>`).join('')}</ul></div></div><div class="boundary-note"><strong>${s.raw_rows_shared} raw transaction rows shared</strong> · ${source==='fixture'?'fixture declaration, not a measured production result':'backend-reported value'}. Institution ID, pseudonymous entity IDs and local risk are also returned for display.</div><div class="case-section-title">SECURITY STATUS & LIMITS</div><p>Confidential execution: <strong>${source==='fixture'?'unverified':s.execution_verified?'backend reports verified; not attested by this UI':'unverified'}</strong>. Pseudonymization is not anonymity. Relationships, risk bands and timing buckets can expose patterns. Authentication, authorization, key management, retention controls and deployment attestation belong to the integrated system.</p><p>The local-only toggle is a visual comparison. It is not an access-control boundary; this browser receives the whole analysis response. Replay history is an in-memory presentation trail, not a tamper-evident backend audit log.</p>`;
}
function renderTrail(view) {
  $('view-audit').innerHTML = `<h3>${source==='fixture'?'Synthetic replay trail':'Backend snapshot relationships'}</h3><p>${source==='fixture'?'A deterministic presentation of the bundled fixture. These are scenario time buckets, not system logs.':'Relationships from the returned analysis. This panel is not a persisted or verified audit log.'}</p><div class="trail-row"><span>INIT</span><div><strong>${data.banks.length} institutions in the scenario</strong><p>${collaborative?'Collaborative relationship view enabled.':'Local view enabled; cross-bank relationships hidden.'}</p></div></div>${view.edges.map(e=>`<div class="trail-row"><span>${esc(e.time_bucket)}</span><div><strong>${esc(e.source)} → ${esc(e.target)}</strong><p>${esc(e.id)} · ${esc(e.kind)} · ${esc(e.risk_band)} risk band</p></div></div>`).join('')}${view.alerts.map(a=>`<div class="trail-row"><span>CASE</span><div><strong>${esc(a.id)} · ${esc(a.title)}</strong><p>${a.edge_ids.length} supporting links; ${a.reasons.length} reason codes. Investigator review required.</p></div></div>`).join('')}`;
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
$('settings-open').onclick=()=>{$('settings-dialog').showModal();};
$('settings-close').onclick=()=>{$('settings-dialog').close();};
$('mock-button').onclick=()=>{if(fixture){setData(structuredClone(fixture),'fixture');$('connection-status').textContent='';$('settings-dialog').close();notify('Restored the synthetic fixture.');}};
$('connection-form').onsubmit=async e=>{
  e.preventDefault();const button=$('connect-button');button.disabled=true;stop();render();
  $('connection-status').textContent='Checking health and loading scenario…';
  try{
    const url=new URL($('api-url').value);if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw new Error('Use an HTTP(S) base URL without embedded credentials.');
    url.search='';url.hash='';const base=url.href.replace(/\/$/,'');
    async function request(path,options={}){
      const response=await fetch(base+path,{...options,signal:AbortSignal.timeout(15000),credentials:'omit',redirect:'error'});
      if(!response.ok)throw new Error(`${path} returned HTTP ${response.status}.`);
      const body=await response.text();if(body.length>2000000)throw new Error('API response exceeds the 2 MB demo limit.');
      try{return JSON.parse(body);}catch{throw new Error(`${path} did not return valid JSON.`);}
    }
    await request('/health');
    const scenario=await request('/demo/scenario');
    if(!scenario.analysis_request||typeof scenario.analysis_request!=='object'||Array.isArray(scenario.analysis_request))throw new Error('GET /demo/scenario must return an analysis_request object.');
    $('connection-status').textContent='Analyzing the scenario with the backend…';
    const result=await request('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(scenario.analysis_request)});
    const next=validateAnalysis(result);setData(next,'api');$('settings-dialog').close();$('connection-status').textContent='';notify('Backend analysis loaded. Replay is available in synthetic demo mode.');
  }catch(error){$('connection-status').textContent=`Connection failed: ${error.message} Current data is unchanged. Check the API URL, CORS and docs/data_contract.md.`;}
  finally{button.disabled=false;}
};
try {
  const response=await fetch('./public/scenario.json');if(!response.ok)throw new Error(`Fixture HTTP ${response.status}`);
  fixture=validateAnalysis(await response.json());setData(structuredClone(fixture),'fixture');
} catch(error) {
  $('metrics').innerHTML=empty('Unable to load the demo',error.message+' Serve this folder over HTTP; see README.md.');
  $('play-button').disabled=$('step-button').disabled=$('reset-button').disabled=true;
  $('connection-status').textContent='The bundled fixture could not load. You can still connect to a compatible API.';
}
