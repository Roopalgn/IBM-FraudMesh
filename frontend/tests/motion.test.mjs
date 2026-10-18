import test from 'node:test';
import assert from 'node:assert/strict';
import {frameSummary} from '../src/motion.js';

test('browser frame reporting excludes invalid intervals and discloses slow frames',()=>{
  const result=frameSummary([16.67,16.7,NaN,-1,0,50,16.5,Infinity]);
  assert.deepEqual(result,{frames:4,p50_ms:16.67,p95_ms:50,max_ms:50});
});
test('absent frame samples do not fabricate smooth playback measurements',()=>{
  assert.equal(frameSummary([]),null);
  assert.equal(frameSummary([NaN,-1]),null);
});
