import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadAnalysis,permittedRequest,safeBaseUrl} from '../src/api.js';
import {validateAnalysis,caseExport,maxStep} from '../src/model.js';
const snapshots=Object.fromEntries(await Promise.all(['common','ring','normal','local'].map(async name=>[name,JSON.parse(await readFile(new URL(`../public/computed/${name}.json`,import.meta.url),'utf8'))])));
const signal={signal_id:'test-reference',institution_id:'bank_a',source_entity_token:'fm1:'+'a'.repeat(64),destination_entity_token:'fm1:'+'b'.repeat(64),timestamp_bucket:'2026-10-17T10:00Z',amount_bucket:'lt_1k',local_risk_score:.2,channel:'online'};
const scenario=()=>({synthetic:true,analysis_request:{scenario_id:'synthetic-ring',shared_signals:[structuredClone(signal)]}});
function fake(overrides={}){const calls=[];return{calls,fetcher:async(url,options)=>{calls.push({url,options});const path=new URL(url).pathname;const value=overrides[path]??(path==='/health'?{synthetic_only:true}:path==='/demo/scenario'?scenario():snapshots.ring.analysis);return{ok:!overrides.status,status:overrides.status||200,text:async()=>typeof value==='string'?value:JSON.stringify(value)};}};}
test('saved authoritative snapshots cover shared, normal and local controls with provenance',()=>{
  for(const saved of Object.values(snapshots)){assert.equal(validateAnalysis(saved.analysis).synthetic,true);assert.equal(saved.provenance.function,'fraudmesh.service.analyze_for_dashboard');assert.equal(Object.keys(saved.provenance.source_sha256).length,4);}
  assert.equal(snapshots.common.analysis.graph.edges.length,21);assert.equal(snapshots.normal.analysis.collaborative_alerts.length,0);assert.equal(snapshots.local.analysis.banks.reduce((n,b)=>n+b.local_ring_count,0),1);
});
test('API flow follows authoritative health/scenario/analyze contract',async()=>{
  const harness=fake();const data=await loadAnalysis('http://localhost:8000','ring',harness);
  assert.deepEqual(harness.calls.map(c=>new URL(c.url).pathname),['/health','/demo/scenario','/analyze']);assert.equal(new URL(harness.calls[1].url).search,'?name=ring');assert.deepEqual(JSON.parse(harness.calls[2].options.body),scenario().analysis_request);assert.equal(data.collaborative_alerts.length,1);assert.equal(harness.calls[2].options.credentials,'omit');
});
test('raw records, secrets and malformed permitted scalar values are rejected before POST',async()=>{
  for(const field of ['customer_rows','secret','transactions']){const value=scenario();value.analysis_request[field]='private';const h=fake({'/demo/scenario':value});await assert.rejects(loadAnalysis('http://localhost:8000','ring',h),/raw rows and secrets/);assert.equal(h.calls.length,2);}
  for(const [field,value] of [['channel',{raw:'data'}],['local_risk_score',true],['timestamp_bucket','2026-02-30T10:00Z'],['amount_bucket','1234.56']]){const s=scenario();s.analysis_request.shared_signals[0][field]=value;assert.throws(()=>permittedRequest(s));}
});
test('safe URL handling refuses embedded credentials, query secrets and non-HTTP protocols',()=>{for(const url of ['file:///tmp/a','https://user:secret@example.com','http://localhost/?key=secret','http://localhost/#secret'])assert.throws(()=>safeBaseUrl(url));});
test('HTTP failure, invalid JSON and invalid response surface without fixture substitution',async()=>{
  await assert.rejects(loadAnalysis('http://localhost:8000','ring',fake({status:503})),/HTTP 503/);await assert.rejects(loadAnalysis('http://localhost:8000','ring',fake({'/analyze':'{broken'})),/valid JSON/);await assert.rejects(loadAnalysis('http://localhost:8000','ring',fake({'/analyze':{synthetic:true,scenario_id:'synthetic-ring'}})),/schema_version/);
});
test('timeouts and cancellation abort outstanding requests',async()=>{
  const fetcher=(_url,{signal})=>new Promise((_resolve,reject)=>{if(signal.aborted)return reject(new Error('aborted'));signal.addEventListener('abort',()=>reject(new Error('aborted')),{once:true});});
  await assert.rejects(loadAnalysis('http://localhost:8000','ring',{fetcher,timeout:10}),/timed out/);const c=new AbortController();c.abort();await assert.rejects(loadAnalysis('http://localhost:8000','ring',{fetcher,signal:c.signal}),/cancelled/);
});
test('scoped backend measurement is retained without inventing latency for saved results',()=>{
  const raw=structuredClone(snapshots.ring.analysis);raw.measurement={analysis_ms:2.5,scope:'Validation and graph only; excludes ML, HTTP and rendering.'};const data=validateAnalysis(raw);assert.equal(data.measurement.analysis_ms,2.5);assert.equal(validateAnalysis(snapshots.ring.analysis).measurement,null);raw.measurement.analysis_ms=-1;assert.throws(()=>validateAnalysis(raw),/measurement/);
});
test('duplicate references and missing supporting endpoints fail validation',()=>{
  let raw=structuredClone(snapshots.ring.analysis);raw.collaborative_alerts[0].edge_ids.push(raw.collaborative_alerts[0].edge_ids[0]);assert.throws(()=>validateAnalysis(raw),/Duplicate/);raw=structuredClone(snapshots.ring.analysis);raw.collaborative_alerts[0].node_ids.pop();assert.throws(()=>validateAnalysis(raw),/supporting edge endpoint/);
});
test('comparison counts are separate from transaction flags and must match local findings',()=>{const raw=structuredClone(snapshots.common.analysis);const data=validateAnalysis(raw);assert.equal(data.comparison.combined_patterns,2);assert.equal(data.comparison.local_patterns,1);assert.equal(data.collaborative_alerts.length,1);raw.comparison.local_only.finding_count=999;assert.throws(()=>validateAnalysis(raw),/comparison/);});
test('saved snapshot exports carry provenance without claiming replay timing',()=>{const data=validateAnalysis(snapshots.ring.analysis);data.provenance=snapshots.ring.provenance;const out=caseExport(data,maxStep(data),true,'snapshot');assert.equal(out.replay_step,null);assert.equal(out.provenance.kind,'saved-computed-synthetic');assert.equal(out.measurement,null);});
test('empty graphs remain valid and do not invent cases',()=>{const raw=structuredClone(snapshots.normal.analysis);raw.graph={nodes:[],edges:[]};for(const bank of raw.banks){bank.entity_count=bank.local_alerts=bank.local_ring_count=0;bank.local_findings=[];}const data=validateAnalysis(raw);assert.equal(data.graph.nodes.length,0);assert.equal(caseExport(data,0,true,'api').collaborative_alerts.length,0);});
test('multiple cases retain distinct validated references and consistent combined counts',()=>{const raw=structuredClone(snapshots.ring.analysis);raw.collaborative_alerts.push({...structuredClone(raw.collaborative_alerts[0]),id:'TEST-SECOND-CASE'});raw.comparison.collaborative.finding_count=2;assert.equal(validateAnalysis(raw).collaborative_alerts.length,2);raw.comparison.collaborative.finding_count=1;assert.throws(()=>validateAnalysis(raw),/comparison/);});
