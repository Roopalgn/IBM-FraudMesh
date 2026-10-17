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
    const memberships = n.bank_ids === undefined ? [n.bank_id] : strings(n.bank_ids, 'bank_ids');
    if (!memberships.length || memberships.some(id => !bankIds.has(id)) || !memberships.includes(n.bank_id)) throw new Error('Invalid entity bank memberships.');
    return { id: string(n.id, 'node.id'), bank_id: n.bank_id, bank_ids: [...new Set(memberships)], label: string(n.label, 'node.label'), local_risk: number(n.local_risk, 'local_risk', 0, 1) };
  });
  unique(nodes, 'nodes');
  const nodeIds = new Set(nodes.map(n => n.id));
  const edges = array(input.graph?.edges, 'graph.edges', 200).map(e => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) throw new Error('Edge references an unknown entity.');
    if (e.institution_id !== undefined && !bankIds.has(e.institution_id)) throw new Error('Edge references an unknown bank.');
    if (e.institution_id !== undefined && [e.source,e.target].some(id => !nodes.find(n=>n.id===id).bank_ids.includes(e.institution_id))) throw new Error('Edge bank is absent from entity memberships.');
    return { id: string(e.id, 'edge.id'), source: e.source, target: e.target, kind: string(e.kind, 'kind'),
      step: integer(e.step, 'step', 1, 200), time_bucket: string(e.time_bucket, 'time_bucket'), risk_band: string(e.risk_band, 'risk_band'),
      ...(e.institution_id === undefined ? {} : {institution_id:e.institution_id, local_risk_score:number(e.local_risk_score,'edge.local_risk_score',0,1)}) };
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
  return { schema_version: '1.0', scenario_id: string(input.scenario_id, 'scenario_id'), synthetic: input.synthetic,
    banks, graph: { nodes, edges }, collaborative_alerts: alerts,
    sharing_summary: { raw_rows_shared: integer(summary.raw_rows_shared, 'raw_rows_shared'),
      shared_fields: strings(summary.shared_fields, 'shared_fields'), retained_local: strings(summary.retained_local, 'retained_local'),
      execution_verified: summary.execution_verified } };
}
export function maxStep(data) {
  return Math.max(0, ...data.graph.edges.map(e => e.step), ...data.collaborative_alerts.map(a => a.detected_at_step));
}
export function deriveView(data, step, collaborative) {
  let nodes = data.graph.nodes;
  let nodeMap = new Map(nodes.map(n => [n.id, n]));
  let edges = data.graph.edges.filter(e => e.step <= step);
  const attributed = edges.every(e => e.institution_id !== undefined);
  if (!collaborative && attributed) {
    // Separate bank-visible copies avoid reconstructing cross-bank paths locally.
    const localNodes = new Map();
    edges = edges.map(e => {
      for (const id of [e.source,e.target]) {
        const key = `${id}@${e.institution_id}`;
        const existing = localNodes.get(key);
        localNodes.set(key,{...nodeMap.get(id),id:key,bank_id:e.institution_id,bank_ids:[e.institution_id],local_risk:Math.max(existing?.local_risk ?? 0,e.local_risk_score)});
      }
      return {...e,source:`${e.source}@${e.institution_id}`,target:`${e.target}@${e.institution_id}`};
    });
    nodes = [...localNodes.values()];
    nodeMap = new Map(nodes.map(n=>[n.id,n]));
  } else if (!collaborative) edges = edges.filter(e=>nodeMap.get(e.source).bank_id === nodeMap.get(e.target).bank_id);
  const alerts = collaborative ? data.collaborative_alerts.filter(a => a.detected_at_step <= step) : [];
  return { nodes, edges, alerts, nodeMap, crossBankEdges: collaborative ? edges.filter(e => attributed ? [e.source,e.target].some(id=>nodeMap.get(id).bank_ids.length>1) : nodeMap.get(e.source).bank_id !== nodeMap.get(e.target).bank_id) : [],
    participatingBanks: new Set(edges.flatMap(e => e.institution_id ? [e.institution_id] : [nodeMap.get(e.source).bank_id,nodeMap.get(e.target).bank_id])).size };
}
export function caseExport(data, step, collaborative, source) {
  const view = deriveView(data, step, collaborative);
  const ids = new Set(view.edges.flatMap(e => [e.source, e.target]));
  return { exported_at: new Date().toISOString(), source, synthetic: data.synthetic, scenario_id: data.scenario_id,
    mode: collaborative ? 'collaborative' : 'local-only', replay_step: step,
    graph: { nodes: view.nodes.filter(n => ids.has(n.id)), edges: view.edges },
    collaborative_alerts: view.alerts, sharing_summary: collaborative ? data.sharing_summary : null,
    limitations: 'Display export only. No inference, privacy, deployment, or security verification is performed by this frontend. Local-only mode is a visualization of the backend or fixture output, not bank-level access control.' };
}
