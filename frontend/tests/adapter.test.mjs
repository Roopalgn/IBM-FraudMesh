import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {adaptGraphResponse} from '../src/graph-adapter.js';
import {deriveView,caseExport,maxStep} from '../src/model.js';
const ring=JSON.parse(await readFile(new URL('../public/integration/ring.json',import.meta.url),'utf8'));
const normal=JSON.parse(await readFile(new URL('../public/integration/normal.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(ring.analysis);
const control=JSON.parse(await readFile(new URL('../public/integration/local-control.json',import.meta.url),'utf8'));
test('corrected single-bank control detects one local structure without a multi-bank requirement',()=>{
  const d=adaptGraphResponse(control.analysis,control);assert.equal(d.banks[0].local_ring_count,1);assert.equal(d.collaborative_alerts.length,1);
  const v=deriveView(d,0,false,'bank_a');assert.equal(v.alerts.length,1);assert.equal(v.edges.length,3);
  const out=caseExport(d,0,false,'computed-fixture','bank_a');assert.equal(out.local_structural_findings.length,1);assert.equal(out.collaborative_alerts.length,0);
});
test('actual graph output maps signal IDs and case evidence without invented scores',()=>{
  const d=adaptGraphResponse(ring.analysis,ring);
  assert.equal(d.collaborative_alerts.length,1);assert.equal(d.graph.nodes.length,3);assert.equal(d.graph.edges.length,3);
  assert.deepEqual(d.graph.edges.map(e=>e.id),ring.analysis.graph.edges.map(e=>e.signal_id));
  assert.equal(d.collaborative_alerts[0].id,ring.analysis.collaborative_alerts[0].alert_id);
  assert.deepEqual(d.collaborative_alerts[0].edge_ids,ring.analysis.collaborative_alerts[0].supporting_signal_ids);
  assert.ok(d.graph.nodes.every(n=>n.local_risk===null));assert.ok(d.graph.edges.every(e=>e.time_bucket==='2026-10-17T10:00Z'&&e.transaction_score!==null));
  assert.equal(d.replay_supported,false);assert.equal(maxStep(d),0);
});
test('shared entity memberships describe contributing signals, not exclusive ownership',()=>{
  const d=adaptGraphResponse(ring.analysis,ring);assert.ok(d.graph.nodes.every(n=>n.bank_ids.length===2&&!Object.hasOwn(n,'bank_id')));
  for(const b of d.banks){const v=deriveView(d,0,false,b.id);assert.equal(v.edges.length,1);assert.equal(v.nodes.length,2);assert.equal(v.alerts.length,0);assert.ok(v.edges.every(e=>e.contributing_bank_id===b.id));}
});
test('missing ML flags are unavailable while corrected local structure counts are supplied',()=>{
  const d=adaptGraphResponse(ring.analysis,ring);assert.ok(d.banks.every(b=>b.local_alerts===null&&b.local_ring_count===0));assert.equal(d.comparison.local_valid,true);
});
test('rows received do not mean rows shared; a bare execution flag cannot verify a TEE',()=>{
  const raw=fresh();raw.privacy.execution_verified=true;const d=adaptGraphResponse(raw,ring);
  assert.equal(d.sharing_summary.raw_rows_received,null);assert.equal(d.sharing_summary.raw_rows_shared,null);assert.equal(d.sharing_summary.execution_verified,false);assert.equal(d.measurement,null);
});
test('generated unrelated activity has no case and records pinned provenance',()=>{
  const d=adaptGraphResponse(normal.analysis,normal);assert.equal(d.collaborative_alerts.length,0);assert.equal(d.graph.nodes.length,6);assert.equal(d.provenance.commit,'34822ed09e167a810abc29cdde5104b569e84b72');
});
test('invalid evidence, contributor casing, duplicate references and counts fail',()=>{
  let r=fresh();r.collaborative_alerts[0].supporting_signal_ids[0]='absent';assert.throws(()=>adaptGraphResponse(r,ring),/missing graph evidence/);
  r=fresh();r.graph.edges[0].institution_id='BANK_A';assert.throws(()=>adaptGraphResponse(r,ring),/unknown contributing/);
  r=fresh();r.collaborative_alerts[0].supporting_signal_ids.push(r.collaborative_alerts[0].supporting_signal_ids[0]);assert.throws(()=>adaptGraphResponse(r,ring),/duplicate evidence/);
  r=fresh();r.summary.structural_findings=4;assert.throws(()=>adaptGraphResponse(r,ring),/summary counts/);
});
test('empty graphs and missing optional declarations are supported',()=>{
  const r=fresh();delete r.privacy.pseudonymization;delete r.privacy.raw_transaction_rows_received;r.bank_results=[];r.collaborative_alerts=[];r.graph={nodes:[],edges:[]};r.summary={signals_processed:0,pseudonymous_entities:0,structural_findings:0};r.comparison.local_only={finding_count:0,findings_by_institution:{}};r.comparison.collaborative={finding_count:0,findings:[]};
  const d=adaptGraphResponse(r,ring);assert.equal(d.sharing_summary.raw_rows_received,null);assert.match(d.sharing_summary.privacy_description,/validates permitted/);assert.equal(deriveView(d,0,true).edges.length,0);
});
test('multiple cases preserve distinct IDs and supporting references',()=>{
  const r=fresh();r.collaborative_alerts.push({...structuredClone(r.collaborative_alerts[0]),alert_id:'test-second'});r.summary.structural_findings=2;r.comparison.collaborative.finding_count=2;r.comparison.collaborative.findings=structuredClone(r.collaborative_alerts);assert.equal(adaptGraphResponse(r,ring).collaborative_alerts.length,2);
});
test('local snapshot exports contain only selected contributor evidence',()=>{
  const d=adaptGraphResponse(ring.analysis,ring),out=caseExport(d,0,false,'computed-fixture','bank_b');assert.equal(out.graph.edges.length,1);assert.equal(out.graph.nodes.length,2);assert.equal(out.collaborative_alerts.length,0);assert.equal(out.replay_step,null);assert.equal(out.provenance.commit,ring.provenance.commit);
});
test('explicit profile and synthetic provenance required; unknown raw fields are projected out',()=>{
  assert.throws(()=>adaptGraphResponse(ring.analysis,{...ring,profile:'guess'}),/explicit profile/);assert.throws(()=>adaptGraphResponse(ring.analysis,{...ring,synthetic:undefined}),/synthetic provenance/);
  const r=fresh();r.customer_rows=['do not export'];r.graph.nodes[0].secret='do not export';assert.ok(!JSON.stringify(adaptGraphResponse(r,ring)).includes('do not export'));
});
