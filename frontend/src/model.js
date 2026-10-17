// Backend boundary: validate and project display fields, never render arbitrary HTML.
const string = (v, path) => {
  if (typeof v !== 'string' || !v.length || v.length > 500) throw new Error(`${path} must be a nonempty string (up to 500 characters).`);
  return v;
};
const number = (v, path, min = 0, max = Number.MAX_SAFE_INTEGER) => {
  if (!Number.isFinite(v) || v < min || v > max) throw new Error(`${path} must be between ${min} and ${max}.`);
  return v;
};
const integer = (v, path, min = 0, max = Number.MAX_SAFE_INTEGER) => {
  number(v, path, min, max);
  if (!Number.isInteger(v)) throw new Error(`${path} must be an integer.`);
  return v;
};
const array = (v, path, max = 500) => {
  if (!Array.isArray(v) || v.length > max) throw new Error(`${path} must be an array of at most ${max} items.`);
  return v;
};
const strings = (v, path) => array(v, path).map(x => string(x, path));
const unique = (items, path) => {
  if (new Set(items.map(x => x.id)).size !== items.length) throw new Error(`${path} contains duplicate IDs.`);
};
export function validateAnalysis(input) {
  if (!input || input.schema_version !== '1.0') throw new Error('Expected analysis schema_version "1.0". See docs/data_contract.md.');
  if (typeof input.synthetic !== 'boolean') throw new Error('synthetic must explicitly be true or false.');
  const banks = array(input.banks, 'banks', 3).map(b => ({
    id: string(b.id, 'bank.id'), name: string(b.name, 'bank.name'),
    entity_count: integer(b.entity_count, 'entity_count'), local_alerts: integer(b.local_alerts, 'local_alerts'),
    local_ring_count: integer(b.local_ring_count, 'local_ring_count'),
    local_findings: b.local_findings === undefined ? [] : array(b.local_findings, 'local_findings', 20).map(f => ({title: string(f.title, 'finding.title'), detail: string(f.detail, 'finding.detail')}))
  }));
  if (!banks.length) throw new Error('At least one bank is required.');
  unique(banks, 'banks');
  const bankIds = new Set(banks.map(b => b.id));
  const nodes = array(input.graph?.nodes, 'graph.nodes', 60).map(n => {
    if (!bankIds.has(n.bank_id)) throw new Error('Node references an unknown bank.');
    return { id: string(n.id, 'node.id'), bank_id: n.bank_id, label: string(n.label, 'node.label'), local_risk: number(n.local_risk, 'local_risk', 0, 1) };
  });
  unique(nodes, 'nodes');
  const nodeIds = new Set(nodes.map(n => n.id));
  const edges = array(input.graph?.edges, 'graph.edges', 200).map(e => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) throw new Error('Edge references an unknown entity.');
    return { id: string(e.id, 'edge.id'), source: e.source, target: e.target, kind: string(e.kind, 'kind'),
      step: integer(e.step, 'step', 1, 200), time_bucket: string(e.time_bucket, 'time_bucket'), risk_band: string(e.risk_band, 'risk_band') };
  });
  unique(edges, 'edges');
  const edgeIds = new Set(edges.map(e => e.id));
  const alerts = array(input.collaborative_alerts, 'collaborative_alerts', 100).map(a => {
    const refs = strings(a.node_ids, 'node_ids');
    const edgeRefs = strings(a.edge_ids, 'edge_ids');
    if (refs.some(id => !nodeIds.has(id)) || edgeRefs.some(id => !edgeIds.has(id))) throw new Error('Alert references missing graph evidence.');
    const step = integer(a.detected_at_step, 'detected_at_step', 1, 200);
    if (edges.some(e => edgeRefs.includes(e.id) && e.step > step)) throw new Error('Alert arrives before its supporting relationships.');
    return { id: string(a.id, 'alert.id'), title: string(a.title, 'alert.title'), severity: string(a.severity, 'severity'),
      detected_at_step: step, node_ids: refs, edge_ids: edgeRefs,
      reasons: array(a.reasons, 'reasons', 20).map(r => ({ code: string(r.code, 'reason.code'), title: string(r.title, 'reason.title'), detail: string(r.detail, 'reason.detail') })) };
  });
  unique(alerts, 'alerts');
  const summary = input.sharing_summary;
  if (!summary || typeof summary.execution_verified !== 'boolean') throw new Error('sharing_summary.execution_verified must be explicit.');
  const normalizedNodes = nodes.map(n=>({...n,bank_ids:[n.bank_id]}));
  const normalizedEdges = edges.map(e=>({...e,contributing_bank_id:nodes.find(n=>n.id===e.source).bank_id===nodes.find(n=>n.id===e.target).bank_id ? nodes.find(n=>n.id===e.source).bank_id : null}));
  return { schema_version: '1.0', scenario_id: string(input.scenario_id, 'scenario_id'), synthetic: input.synthetic,
    replay_supported:true,comparison:{local_valid:true,note:'Authored demonstration counts, not a computed accuracy comparison.'},
    banks, graph: { nodes:normalizedNodes, edges:normalizedEdges }, collaborative_alerts: alerts,
    sharing_summary: { raw_rows_shared: integer(summary.raw_rows_shared, 'raw_rows_shared'),
      shared_fields: strings(summary.shared_fields, 'shared_fields'), retained_local: strings(summary.retained_local, 'retained_local'),
      execution_verified: summary.execution_verified } };
}
export function maxStep(data) {
  return Math.max(0, ...data.graph.edges.map(e => e.step), ...data.collaborative_alerts.map(a => a.detected_at_step));
}
export function deriveView(data, step, collaborative, bankId = null) {
  const nodeMap = new Map(data.graph.nodes.map(n => [n.id, n]));
  const edges = data.graph.edges.filter(e => e.step <= step && (collaborative || (e.contributing_bank_id !== null && (!bankId || e.contributing_bank_id===bankId))));
  const visibleIds=new Set(edges.flatMap(e=>[e.source,e.target]));
  const nodes=collaborative ? data.graph.nodes : data.graph.nodes.filter(n=>visibleIds.has(n.id));
  const visibleEdgeIds=new Set(edges.map(e=>e.id));
  const candidates=collaborative?data.collaborative_alerts:data.banks.filter(b=>!bankId||b.id===bankId).flatMap(b=>b.local_structural_findings||[]);
  const alerts = candidates.filter(a => a.detected_at_step <= step && a.edge_ids.every(id=>visibleEdgeIds.has(id)));
  return { edges, nodes, alerts, nodeMap, crossBankEdges: edges.filter(e => e.contributing_bank_id===null),
    participatingBanks: new Set(edges.map(e=>e.contributing_bank_id).filter(Boolean)).size };
}
export function caseExport(data, step, collaborative, source, bankId=null) {
  const view = deriveView(data, step, collaborative, bankId);
  const ids = new Set(view.edges.flatMap(e => [e.source, e.target]));
  return { exported_at: new Date().toISOString(), source, synthetic: data.synthetic, scenario_id: data.scenario_id,
    mode: collaborative ? 'collaborative' : 'local-only', selected_bank: bankId, replay_step: data.replay_supported ? step : null,
    graph: { nodes: data.graph.nodes.filter(n => ids.has(n.id)), edges: view.edges },
    collaborative_alerts: collaborative ? view.alerts : [], local_structural_findings: collaborative ? [] : view.alerts, sharing_summary: collaborative ? data.sharing_summary : null,
    provenance:data.saved_provenance||data.provenance||null,measurement:data.measurement||null,
    limitations: 'Display export only. No inference, privacy, deployment, or security verification is performed by this frontend. Local-only mode is a visualization of the backend or fixture output, not bank-level access control. Membership describes incidence in bank-contributed signals, not account ownership.' };
}
