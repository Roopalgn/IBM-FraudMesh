// Presentation helpers only. No model, graph rules, or API schema changes.
export const SCENARIOS = Object.freeze({api:'Shared team scenario','api-ring':'Cross-bank ring','api-normal':'Normal activity','api-local':'Local positive control'});
export const BANK_COLORS = ['#60A5FA','#A78BFA','#F3B86B'];
export function sourceBadge(origin,synthetic=true,service='') { return origin==='fixture'?'Authored synthetic replay':origin==='computed-fixture'?'Saved computed snapshot':service==='frontend-contract-test-harness'?'API test harness · synthetic':synthetic?'API · synthetic data':'API · backend output'; }
export function scenarioTitle(choice) { return SCENARIOS[choice] || ({authored:'Authored synthetic replay',ring:'Saved ring snapshot',normal:'Saved normal snapshot','local-control':'Saved local control'}[choice]) || 'Investigation'; }
export function riskDisplay(triage) { return triage ? `${triage.priority_score.toFixed(3)} / 1.000` : 'Not supplied'; }
export function filterEvidence(edges, query='', bank='all') { const q=query.trim().toLowerCase();return edges.filter(e=>(bank==='all'||e.contributing_bank_id===bank)&&[e.id,e.source,e.target,e.time_bucket,e.amount_bucket].join(' ').toLowerCase().includes(q)); }
export function journalLabel(status) { return status==null?'Not checked':status.valid===true?'Local chain consistent':status.valid===false?'Integrity check failed':'Unavailable'; }
export function crossBankCaseCount(data, alerts) {
  const contributors = new Map(data.graph.edges.map(edge=>[edge.id,edge.contributing_bank_id]));
  return alerts.filter(alert=>new Set(alert.edge_ids.map(id=>contributors.get(id)).filter(Boolean)).size>1).length;
}
export function graphPositions(nodes) {
  const sorted=[...nodes].sort((a,b)=>a.label.localeCompare(b.label));
  if(sorted.length<=8)return new Map(sorted.map((n,i)=>{const angle=-Math.PI/2+i*2*Math.PI/Math.max(1,sorted.length);return[n.id,[440+260*Math.cos(angle),220+140*Math.sin(angle)]];}));
  const cols=Math.min(7,Math.ceil(Math.sqrt(sorted.length*1.7))),rows=Math.ceil(sorted.length/cols);
  return new Map(sorted.map((n,i)=>[n.id,[95+(i%cols)*690/Math.max(1,cols-1),65+Math.floor(i/cols)*325/Math.max(1,rows-1)]]));
}
export const ICONS = {
  spark:'<path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z"/>',
  network:'<circle cx="5" cy="6" r="2"/><circle cx="18" cy="5" r="2"/><circle cx="12" cy="18" r="2"/><path d="m7 6 9-1M6 8l5 8m6-9-4 9"/>',
  evidence:'<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7m-7 4h7"/>',
  privacy:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
  audit:'<path d="M19 8a8 8 0 1 0 1 7M19 3v5h-5M12 7v5l3 2"/>',
  settings:'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
  export:'<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
  arrow:'<path d="M4 12h15m-6-6 6 6-6 6"/>',
  bank:'<path d="m3 8 9-5 9 5H3m2 3v7m7-7v7m7-7v7M3 21h18"/>',
  case:'<rect x="3" y="6" width="18" height="15" rx="2"/><path d="M8 6V3h8v3m-13 7h18m-10 0v3h2v-3"/>',
  check:'<path d="m5 12 4 4L19 6"/>', search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
};
export function icon(name) { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.network}</svg>`; }
export function logo(monochrome=false) {return `<svg class="mesh-logo" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="m20 5 14 24H6L20 5Zm0 13v17M8 29l12-11 12 11" stroke="${monochrome?'currentColor':'#4BE0C1'}" stroke-width="1.8" stroke-linejoin="round"/><path d="m20 5 0 13M6 29l14 6 14-6" stroke="currentColor" stroke-opacity=".4" stroke-width="1.5"/><circle cx="20" cy="5" r="3" fill="${monochrome?'currentColor':'#60A5FA'}"/><circle cx="6" cy="29" r="3" fill="${monochrome?'currentColor':'#A78BFA'}"/><circle cx="34" cy="29" r="3" fill="${monochrome?'currentColor':'#F3B86B'}"/><circle cx="20" cy="18" r="3.5" fill="${monochrome?'currentColor':'#4BE0C1'}"/></svg>`;}
