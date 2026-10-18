import test from 'node:test';
import assert from 'node:assert/strict';
import {SCENARIOS,scenarioTitle,sourceBadge,filterEvidence,journalLabel,graphPositions,riskDisplay,logo,icon,crossBankCaseCount} from '../src/workspace.js';
import {readFile} from 'node:fs/promises';
import {validateAnalysis,deriveView,maxStep} from '../src/model.js';

test('authored cross-bank comparison stays zero until the last supporting replay event, including after reset',async()=>{
 const data=validateAnalysis(JSON.parse(await readFile(new URL('../public/scenario.json',import.meta.url),'utf8')));
 const last=maxStep(data);
 assert.ok(last>1);
 for(let step=0;step<last;step++)assert.equal(crossBankCaseCount(data,deriveView(data,step,true).alerts),0,`partial step ${step}`);
 assert.equal(crossBankCaseCount(data,deriveView(data,last,true).alerts),1);
 assert.equal(crossBankCaseCount(data,deriveView(data,0,true).alerts),0,'reset after completion');
 assert.equal(crossBankCaseCount(data,deriveView(data,last,false,data.banks[0].id).alerts),0,'local scope');
});

test('all four live scenario titles remain distinct from saved and authored sources',()=>{
 assert.equal(Object.keys(SCENARIOS).length,4);
 assert.equal(scenarioTitle('api'),'Shared team scenario');
 assert.equal(scenarioTitle('api-ring'),'Cross-bank ring');
 assert.equal(scenarioTitle('api-normal'),'Normal activity');
 assert.equal(scenarioTitle('api-local'),'Local positive control');
 assert.match(scenarioTitle('authored'),/Authored/);
 assert.match(scenarioTitle('ring'),/Saved/);
});
test('source badges never present a saved fixture as a live API or computed detection',()=>{
 assert.equal(sourceBadge('fixture'),'Authored synthetic replay');
 assert.equal(sourceBadge('computed-fixture'),'Saved computed snapshot');
 assert.equal(sourceBadge('api',true),'API · synthetic data');
 assert.equal(sourceBadge('api',false),'API · backend output');
 assert.match(sourceBadge('api',true,'frontend-contract-test-harness'),/test harness/);
});
test('evidence filter preserves original references for graph-linked selection without mutation',()=>{
 const rows=[{id:'signal-A',source:'fm1:a',target:'fm1:b',contributing_bank_id:'bank_a',time_bucket:'2026-10-17T10:00Z',amount_bucket:'lt_1k'},{id:'signal-B',source:'fm1:b',target:'fm1:c',contributing_bank_id:'bank_b',time_bucket:'2026-10-17T11:00Z',amount_bucket:'1k_10k'}];
 const before=structuredClone(rows);
 assert.deepEqual(filterEvidence(rows,'SIGNAL-a'),[rows[0]]);
 assert.deepEqual(filterEvidence(rows,'','bank_b'),[rows[1]]);
 assert.deepEqual(filterEvidence(rows,'11:00','bank_a'),[]);
 assert.deepEqual(filterEvidence(rows,'fm1:b'),rows);
 assert.deepEqual(rows,before);
});
test('graph positions are deterministic under input reordering and labels stay in framing',()=>{
 for(const count of [0,3,6,21,60]){
 const nodes=Array.from({length:count},(_,i)=>({id:String(i),label:`Entity ${String(i).padStart(2,'0')}`}));
 const positions=graphPositions(nodes);
 assert.deepEqual(positions,graphPositions([...nodes].reverse()));
 for(const [x,y] of positions.values()){assert.ok(x>=50&&x<=830);assert.ok(y>=45&&y+65<=460);}
 }
});
test('audit labels distinguish absence, actual failure, and computed consistency',()=>{
 assert.equal(journalLabel(null),'Not checked');
 assert.equal(journalLabel({}),'Unavailable');
 assert.equal(journalLabel({valid:true}),'Local chain consistent');
 assert.equal(journalLabel({valid:false}),'Integrity check failed');
});
test('review display does not create probability values when triage is absent',()=>{
 assert.equal(riskDisplay(null),'Not supplied');
 assert.equal(riskDisplay({priority_score:.809}),'0.809 / 1.000');
});
test('original brand and icon marks use inline SVG with accessible decorative semantics',()=>{
 assert.match(logo(),/<svg/);assert.match(logo(true),/currentColor/);
 assert.match(icon('evidence'),/aria-hidden="true"/);
});
