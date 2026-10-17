import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {existsSync} from 'node:fs';
import {adaptGraphResponse,GRAPH_PROFILE} from '../src/graph-adapter.js';
import {deriveView,caseExport} from '../src/model.js';
import {loadAnalysis} from '../src/api.js';
const root=fileURLToPath(new URL('../../',import.meta.url));
const venv=fileURLToPath(new URL(process.platform==='win32'?'../../.venv/Scripts/python.exe':'../../.venv/bin/python',import.meta.url));
const python=process.env.FRAUDMESH_TEST_PYTHON||(existsSync(venv)?venv:'python');
const generated=spawnSync(python,['-B','-c',"import runpy; runpy.run_path('tests/export_frontend_fixtures.py',run_name='__main__')"],{cwd:root,encoding:'utf8'});
if(generated.status!==0)throw new Error(generated.stderr);
const outputs=JSON.parse(generated.stdout);
const adapt=name=>adaptGraphResponse(outputs[name].analysis,{profile:GRAPH_PROFILE,scenario_id:outputs[name].scenario.scenario_id,synthetic:true});
test('actual API responses adapt with structured evidence and ML-informed review policy',()=>{
 for(const name of Object.keys(outputs))assert.equal(adapt(name).synthetic,true);
 assert.equal(adapt('common').graph.edges.length,21);
 assert.equal(adapt('common').collaborative_alerts.length,2);
 assert.equal(adapt('common').review_queue.combined_recommended,1);
 assert.equal(adapt('normal').collaborative_alerts.length,0);
 assert.equal(adapt('local').banks.reduce((sum,b)=>sum+b.local_ring_count,0),1);
 assert.equal(adapt('common').sharing_summary.raw_rows_shared,null);
});
test('selected bank views and exports contain only contributor evidence',()=>{
 const data=adapt('common'),view=deriveView(data,0,false,'bank_b');
 assert.ok(view.edges.length>0);
 assert.ok(view.edges.every(edge=>edge.contributing_bank_id==='bank_b'));
 const exported=caseExport(data,0,false,'api','bank_b');
 assert.ok(exported.graph.edges.every(e=>exported.graph.nodes.some(n=>n.id===e.source)&&exported.graph.nodes.some(n=>n.id===e.target)));
});
test('API client accepts actual server envelopes and sends only scenario references',async()=>{
 const calls=[];
 const fetcher=async(url,options)=>{calls.push({url,options});const p=new URL(url).pathname;return{ok:true,status:200,text:async()=>JSON.stringify(p==='/health'?{service:'fraudmesh-computed-analysis'}:p==='/demo/scenario'?outputs.common.scenario:outputs.common.analysis)};};
 const result=await loadAnalysis('http://localhost:8000',{fetcher});
 assert.deepEqual(JSON.parse(calls[2].options.body),{scenario_id:'synthetic-common'});
 assert.equal(result.graph.edges.length,21);
 assert.equal(result.api_service,'fraudmesh-computed-analysis');
});
test('invalid contributor attribution remains rejected',()=>{
 const broken=structuredClone(outputs.ring.analysis);broken.graph.edges[0].institution_id='unknown';
 assert.throws(()=>adaptGraphResponse(broken,{profile:GRAPH_PROFILE,scenario_id:'synthetic-ring',synthetic:true}),/contributing institution/);
});
