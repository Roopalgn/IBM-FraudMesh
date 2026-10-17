import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {safeBaseUrl,scenarioMetadata,loadAnalysis} from '../src/api.js';
const fixture=JSON.parse(await readFile(new URL('../public/integration/ring.json',import.meta.url),'utf8'));
const scenario={response_profile:'person3.graph.v2',scenario_id:'test-ring',synthetic:true,analysis_request:{scenario_id:'test-ring'}};
const fake=(overrides={})=>{const calls=[];const fetcher=async(url,options)=>{
  calls.push({url,options});const path=new URL(url).pathname;const body=overrides[path]??(path==='/health'?{status:'ok'}:path==='/demo/scenario'?scenario:fixture.analysis);
  return {ok:!overrides.status,status:overrides.status||200,text:async()=>typeof body==='string'?body:JSON.stringify(body)};};return{calls,fetcher};};
test('endpoint sequence sends only the scenario reference and preserves synthetic provenance',async()=>{
  const {calls,fetcher}=fake();const d=await loadAnalysis('http://localhost:8000',{fetcher});assert.deepEqual(calls.map(c=>new URL(c.url).pathname),['/health','/demo/scenario','/analyze']);assert.deepEqual(JSON.parse(calls[2].options.body),{scenario_id:'test-ring'});assert.equal(d.synthetic,true);assert.equal(d.replay_supported,false);assert.equal(calls[2].options.credentials,'omit');
});
test('raw rows and secrets in scenario requests are rejected before POST',async()=>{
  for(const forbidden of ['customer_rows','transactions','secret','shared_signals']){const s=structuredClone(scenario);s.analysis_request[forbidden]=[];const {calls,fetcher}=fake({'/demo/scenario':s});await assert.rejects(loadAnalysis('http://localhost:8000',{fetcher}),/only the matching scenario_id/);assert.equal(calls.length,2);}
});
test('unsafe URLs and silent schema guessing are rejected',()=>{
  for(const v of ['file:///tmp/a','https://user:secret@example.com','http://host/?key=abc','http://host/#key'])assert.throws(()=>safeBaseUrl(v));assert.throws(()=>scenarioMetadata({analysis_request:{scenario_id:'x'}}),/declare response_profile/);
});
test('HTTP failures, invalid JSON and contract errors surface without fallback',async()=>{
  await assert.rejects(loadAnalysis('http://localhost:8000',fake({status:503})),/HTTP 503/);await assert.rejects(loadAnalysis('http://localhost:8000',fake({'/analyze':'{bad json'})),/valid JSON/);await assert.rejects(loadAnalysis('http://localhost:8000',fake({'/analyze':{}})),/Graph contract/);
});
test('timeouts and cancellation abort requests',async()=>{
  const fetcher=(_url,{signal})=>new Promise((_resolve,reject)=>{if(signal.aborted){reject(new Error('abort'));return;}signal.addEventListener('abort',()=>reject(new Error('abort')),{once:true});});
  await assert.rejects(loadAnalysis('http://localhost:8000',{fetcher,timeout:10}),/timed out/);const c=new AbortController();c.abort();await assert.rejects(loadAnalysis('http://localhost:8000',{fetcher,signal:c.signal}),/cancelled/);
});
