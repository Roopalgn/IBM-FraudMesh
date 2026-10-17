import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateAnalysis, deriveView, maxStep, caseExport } from '../src/model.js';
const input=JSON.parse(await readFile(new URL('../public/scenario.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(input);
const data=validateAnalysis(input);

test('fixture forms one directed six-entity cycle spanning three banks',()=>{
  assert.equal(data.synthetic,true);
  const edges=data.graph.edges;
  let current=edges[0].source;const visited=new Set();
  for(let i=0;i<6;i++){assert.ok(!visited.has(current));visited.add(current);current=edges.find(e=>e.source===current).target;}
  assert.equal(current,edges[0].source);assert.equal(visited.size,6);
  assert.equal(new Set(data.graph.nodes.map(n=>n.bank_id)).size,3);
});
test('local-only view contains three disconnected links and no collaborative cases',()=>{
  const view=deriveView(data,maxStep(data),false);
  assert.equal(view.edges.length,3);assert.equal(view.alerts.length,0);assert.equal(view.crossBankEdges.length,0);
  for(const e of view.edges)assert.equal(view.nodeMap.get(e.source).bank_id,view.nodeMap.get(e.target).bank_id);
});
test('replay never reveals future edges or the case before its final evidence',()=>{
  for(let step=0;step<6;step++){
    const view=deriveView(data,step,true);assert.equal(view.edges.length,step);assert.equal(view.alerts.length,0);
    assert.ok(view.edges.every(e=>e.step<=step));
  }
  assert.equal(deriveView(data,6,true).alerts.length,1);
});
test('fixture shared relationships have no raw transaction fields',()=>{
  const allowed=new Set(['id','source','target','kind','step','time_bucket','risk_band']);
  assert.equal(input.sharing_summary.raw_rows_shared,0);
  for(const edge of input.graph.edges)assert.deepEqual(new Set(Object.keys(edge)),allowed);
  const prohibited=['customer_name','account_number','email','amount','timestamp','raw_transactions'];
  for(const field of prohibited)assert.equal(JSON.stringify(input).includes(`"${field}"`),false);
});
test('local export excludes cross-bank edges, cases and shared summary',()=>{
  const out=caseExport(data,6,false,'fixture');
  assert.equal(out.graph.edges.length,3);assert.equal(out.collaborative_alerts.length,0);assert.equal(out.sharing_summary,null);
  assert.equal(out.synthetic,true);assert.equal(out.mode,'local-only');
});
test('partial export cannot leak future graph evidence',()=>{
  const out=caseExport(data,1,true,'fixture');
  assert.equal(out.graph.edges.length,1);assert.equal(out.graph.nodes.length,2);assert.equal(out.collaborative_alerts.length,0);
});
test('unknown raw payload fields are omitted from normalized output and export',()=>{
  const dirty=fresh();dirty.raw_transactions=[{account_number:'sensitive'}];dirty.graph.nodes[0].customer_name='sensitive';
  const clean=validateAnalysis(dirty);
  assert.ok(!JSON.stringify(caseExport(clean,6,true,'api')).includes('sensitive'));
});
test('unknown bank, unknown node and duplicate relationship IDs are rejected',()=>{
  let x=fresh();x.graph.nodes[0].bank_id='missing';assert.throws(()=>validateAnalysis(x),/unknown bank/);
  x=fresh();x.graph.edges[0].target='missing';assert.throws(()=>validateAnalysis(x),/unknown entity/);
  x=fresh();x.graph.edges[1].id=x.graph.edges[0].id;assert.throws(()=>validateAnalysis(x),/duplicate/);
});
test('invalid risk, fractional counts, missing evidence and premature cases fail validation',()=>{
  let x=fresh();x.graph.nodes[0].local_risk=4;assert.throws(()=>validateAnalysis(x),/local_risk/);
  x=fresh();x.banks[0].local_alerts=.5;assert.throws(()=>validateAnalysis(x),/integer/);
  x=fresh();x.collaborative_alerts[0].edge_ids=['unknown'];assert.throws(()=>validateAnalysis(x),/missing graph evidence/);
  x=fresh();x.collaborative_alerts[0].detected_at_step=2;assert.throws(()=>validateAnalysis(x),/before its supporting/);
});
test('API must label synthetic provenance, schema version and execution status explicitly',()=>{
  let x=fresh();delete x.synthetic;assert.throws(()=>validateAnalysis(x),/synthetic/);
  x=fresh();x.schema_version='2.0';assert.throws(()=>validateAnalysis(x),/schema_version/);
  x=fresh();delete x.sharing_summary.execution_verified;assert.throws(()=>validateAnalysis(x),/execution_verified/);
});
