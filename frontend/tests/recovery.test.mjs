import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {loadAnalysis} from '../src/api.js';
import {adaptGraphResponse} from '../src/graph-adapter.js';
import {caseExport} from '../src/model.js';
const names=['common','ring','normal','local'];
const snapshots=Object.fromEntries(await Promise.all(names.map(async name=>[name,JSON.parse(await readFile(new URL(`../public/computed/${name}.json`,import.meta.url),'utf8'))])));
test('saved primary API examples carry source provenance matching current backend files',async()=>{
 for(const snapshot of Object.values(snapshots)){assert.equal(snapshot.profile,'person3.graph.v2');assert.equal(snapshot.provenance.function,'fraudmesh.analysis.analyze_signals');for(const [path,digest]of Object.entries(snapshot.provenance.source_sha256)){const bytes=await readFile(new URL('../../'+path,import.meta.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),digest);}}
});
test('saved outputs equal actual current backend computation rather than authored detector outcomes',()=>{
 const python=process.env.FRAUDMESH_TEST_PYTHON||'python';const result=spawnSync(python,['-B','-c',"import json;from fraudmesh.demo import demo_request;from fraudmesh.analysis import analyze_signals;print(json.dumps({n:analyze_signals(demo_request(n)['shared_signals']) for n in ['common','ring','normal','local']}))"],{cwd:fileURLToPath(new URL('../../',import.meta.url)),encoding:'utf8'});assert.equal(result.status,0,result.stderr);const actual=JSON.parse(result.stdout);for(const name of names)assert.deepEqual(snapshots[name].analysis,actual[name]);
});
test('saved controls preserve structure and ML-informed review outputs as different quantities',()=>{
 const adapt=name=>adaptGraphResponse(snapshots[name].analysis,snapshots[name]);
 assert.equal(adapt('common').collaborative_alerts.length,2);assert.equal(adapt('common').review_queue.combined_recommended,1);assert.equal(adapt('normal').collaborative_alerts.length,0);assert.equal(adapt('local').banks.reduce((n,b)=>n+b.local_ring_count,0),1);
});
test('optional scoped timing survives adaptation; missing and invalid timings cannot become invented latency',()=>{
 const saved=snapshots.ring,raw=structuredClone(saved.analysis);raw.measurement={analysis_ms:2.5,scope:'Includes bank-local preparation; excludes HTTP and journal write.'};assert.equal(adaptGraphResponse(raw,saved).measurement.analysis_ms,2.5);assert.equal(adaptGraphResponse(saved.analysis,saved).measurement,null);raw.measurement.analysis_ms=-1;assert.throws(()=>adaptGraphResponse(raw,saved),/measurement/);
});
test('saved exports include artifact provenance and never claim authored replay steps',()=>{
 const saved=snapshots.ring,data=adaptGraphResponse(saved.analysis,saved);data.saved_provenance=saved.provenance;const out=caseExport(data,0,true,'saved-api');assert.equal(out.provenance.kind,'saved-computed-synthetic');assert.equal(out.replay_step,null);assert.equal(out.measurement,null);
});
test('scenario-specific live requests use the current reference contract, not old raw signal envelopes',async()=>{
 const saved=snapshots.normal,calls=[];const fetcher=async(url,options)=>{calls.push({url,options});return{ok:true,status:200,text:async()=>JSON.stringify(new URL(url).pathname==='/health'?{service:'fraudmesh-computed-analysis'}:new URL(url).pathname==='/demo/scenario'?{response_profile:saved.profile,scenario_id:saved.scenario_id,synthetic:true,analysis_request:{scenario_id:saved.scenario_id}}:saved.analysis)};};const out=await loadAnalysis('http://localhost:8000',{fetcher,scenarioName:'normal'});assert.equal(new URL(calls[1].url).search,'?name=normal');assert.deepEqual(JSON.parse(calls[2].options.body),{scenario_id:'synthetic-normal'});assert.equal(out.collaborative_alerts.length,0);await assert.rejects(loadAnalysis('http://localhost:8000',{fetcher,scenarioName:'unknown'}),/Unknown/);
});
