import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { validateAnalysis, deriveView, maxStep, caseExport } from '../src/model.js';

const root = fileURLToPath(new URL('../../', import.meta.url));
const venvPython = fileURLToPath(new URL(process.platform==='win32'?'../../.venv/Scripts/python.exe':'../../.venv/bin/python',import.meta.url));
const python = process.env.FRAUDMESH_TEST_PYTHON || (existsSync(venvPython)?venvPython:'python');
const generated = spawnSync(python,['-B','-c',
  'import json; from fraudmesh.demo import demo_request; from fraudmesh.service import analyze_for_dashboard; print(json.dumps({name: analyze_for_dashboard(**{ "signals":demo_request(name)["shared_signals"], "scenario_id":"synthetic-"+name}) for name in ["common","ring","normal","local"]}))'],
  {cwd:root,encoding:'utf8'});
if(generated.status!==0) throw new Error(`Backend fixture generation failed: ${generated.stderr}`);
const outputs = JSON.parse(generated.stdout);

test('actual computed backend responses satisfy the dashboard contract',()=>{
  for(const output of Object.values(outputs)) assert.equal(validateAnalysis(output).synthetic,true);
  assert.equal(validateAnalysis(outputs.ring).collaborative_alerts.length,1);
  assert.equal(validateAnalysis(outputs.normal).collaborative_alerts.length,0);
  assert.equal(validateAnalysis(outputs.local).banks.reduce((sum,b)=>sum+b.local_ring_count,0),1);
});

test('shared team scenario preserves 21 computed signals and does not invent an audited raw-row count',()=>{
  const data=validateAnalysis(outputs.common);
  assert.equal(data.graph.edges.length,21);
  assert.equal(data.collaborative_alerts.length,1);
  assert.equal(data.banks.reduce((sum,b)=>sum+b.local_ring_count,0),1);
  assert.equal(data.sharing_summary.raw_rows_shared,null);
  for(const reason of data.collaborative_alerts[0].reasons) assert.ok(reason.code&&reason.title&&reason.detail);
});

test('local views preserve all bank-contributed signals without joining banks',()=>{
  const data=validateAnalysis(outputs.ring);
  const view=deriveView(data,maxStep(data),false);
  assert.equal(view.edges.length,data.graph.edges.length);
  assert.equal(view.alerts.length,0);
  for(const edge of view.edges){
    assert.equal(view.nodeMap.get(edge.source).bank_id,edge.institution_id);
    assert.equal(view.nodeMap.get(edge.target).bank_id,edge.institution_id);
  }
  const exported=caseExport(data,maxStep(data),false,'api');
  assert.ok(exported.graph.edges.every(e=>exported.graph.nodes.some(n=>n.id===e.source)&&exported.graph.nodes.some(n=>n.id===e.target)));
});

test('shared entity memberships are retained and invalid attribution is rejected',()=>{
  const data=validateAnalysis(outputs.ring);
  assert.ok(data.graph.nodes.some(n=>n.bank_ids.length>1));
  const broken=structuredClone(outputs.ring);
  broken.graph.edges[0].institution_id='unrecognized';
  assert.throws(()=>validateAnalysis(broken),/unknown bank/);
});
