// The authoritative schema is docs/data_contract.md at the repository root.
import {validateAnalysis} from './model.js';
const fields=['signal_id','institution_id','source_entity_token','destination_entity_token','timestamp_bucket','amount_bucket','local_risk_score','channel'];
export function safeBaseUrl(value){
  const url=new URL(value);
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('Use an HTTP(S) base URL without credentials, query parameters or fragments.');
  return url.href.replace(/\/$/,'');
}
export function permittedRequest(scenario){
  if(scenario?.synthetic!==true)throw new Error('Scenario must explicitly declare synthetic data.');
  const request=scenario.analysis_request;
  if(!request||typeof request!=='object'||Array.isArray(request)||Object.keys(request).sort().join(',')!=='scenario_id,shared_signals')throw new Error('Expected scenario_id and permitted shared_signals only; raw rows and secrets are not accepted.');
  if(!['synthetic-common','synthetic-ring','synthetic-normal','synthetic-local','synthetic-custom'].includes(request.scenario_id)||!Array.isArray(request.shared_signals)||request.shared_signals.length>200)throw new Error('Invalid synthetic scenario reference or signal count.');
  const tokens=new Set(),ids=new Set();
  for(const s of request.shared_signals){
    if(!s||typeof s!=='object'||Object.keys(s).sort().join(',')!==[...fields].sort().join(','))throw new Error('Only the documented shared-signal fields may be forwarded.');
    if(typeof s.signal_id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(s.signal_id)||ids.has(s.signal_id))throw new Error('Invalid or duplicate signal reference.');ids.add(s.signal_id);
    if(!['bank_a','bank_b','bank_c'].includes(s.institution_id))throw new Error('Invalid contributing institution.');
    for(const key of ['source_entity_token','destination_entity_token']){if(typeof s[key]!=='string'||!/^fm1:[0-9a-f]{64}$/.test(s[key]))throw new Error('Invalid pseudonymous token representation.');tokens.add(s[key]);}
    if(typeof s.timestamp_bucket!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:00Z$/.test(s.timestamp_bucket)||!Number.isFinite(Date.parse(s.timestamp_bucket))||new Date(s.timestamp_bucket).toISOString().slice(0,16)+'Z'!==s.timestamp_bucket)throw new Error('Expected a valid UTC hour bucket.');
    if(!['lt_1k','1k_10k','10k_50k','gte_50k'].includes(s.amount_bucket)||typeof s.local_risk_score!=='number'||!Number.isFinite(s.local_risk_score)||s.local_risk_score<0||s.local_risk_score>1||!(s.channel===null||['transfer','online','card','ach','wire','upi','mobile','atm'].includes(s.channel)))throw new Error('Invalid shared bucket, score or channel.');
  }
  if(tokens.size>60||new TextEncoder().encode(JSON.stringify(request)).length>128000)throw new Error('Scenario exceeds the documented display/request limits.');
  return request;
}
export async function loadAnalysis(baseValue,name,{fetcher=fetch,onProgress=()=>{},signal,timeout=15000}={}){
  const base=safeBaseUrl(baseValue);
  if(!['common','ring','normal','local'].includes(name))throw new Error('Unknown demo scenario.');
  async function request(path,options={}){
    const controller=new AbortController(),abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)controller.abort();
    const timer=setTimeout(abort,timeout);
    try{const response=await fetcher(base+path,{...options,signal:controller.signal,credentials:'omit',redirect:'error'});
      if(!response.ok)throw new Error(`${path} returned HTTP ${response.status}.`);
      const text=await response.text();if(text.length>2000000)throw new Error('Response exceeds the 2 MB display limit.');
      try{return JSON.parse(text);}catch{throw new Error(`${path} did not return valid JSON.`);}
    }catch(error){if(controller.signal.aborted)throw new Error(signal?.aborted?'Connection cancelled.':`${path} timed out.`);throw error;}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
  }
  onProgress('Checking API health…');const health=await request('/health');
  if(!health||typeof health!=='object'||health.synthetic_only!==true)throw new Error('API health must declare synthetic_only=true.');
  onProgress('Loading permitted scenario signals…');const body=permittedRequest(await request('/demo/scenario?name='+encodeURIComponent(name)));
  onProgress('Computing analysis…');const output=await request('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(output?.synthetic!==true||output.scenario_id!==body.scenario_id)throw new Error('Response must preserve the requested scenario and synthetic provenance.');
  return validateAnalysis(output);
}
