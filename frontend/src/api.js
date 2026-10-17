import {GRAPH_PROFILE,adaptGraphResponse} from './graph-adapter.js';
export function safeBaseUrl(value) {
  const url=new URL(value);
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('Use an HTTP(S) API URL without credentials, query parameters or fragments.');
  return url.href.replace(/\/$/,'');
}
export function scenarioMetadata(scenario) {
  if(!scenario || scenario.response_profile!==GRAPH_PROFILE || typeof scenario.scenario_id!=='string' || !scenario.scenario_id || typeof scenario.synthetic!=='boolean')throw new Error(`Scenario must declare response_profile ${GRAPH_PROFILE}, scenario_id and synthetic. Lead approval of this proposed endpoint envelope is pending.`);
  const request=scenario.analysis_request;
  // One minimal scenario-reference request. Never forward raw rows or secrets from a scenario response.
  if(!request || typeof request!=='object' || Array.isArray(request) || Object.keys(request).length!==1 || request.scenario_id!==scenario.scenario_id)throw new Error('analysis_request must contain only the matching scenario_id; raw records and tokenization secrets are not accepted.');
  return {profile:scenario.response_profile,scenario_id:scenario.scenario_id,synthetic:scenario.synthetic,request};
}
export async function loadAnalysis(value,{fetcher=fetch,onProgress=()=>{},timeout=15000,signal,scenarioName='common'}={}) {
  const base=safeBaseUrl(value);
  async function request(path,options={}){
    const controller=new AbortController();
    const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)controller.abort();
    const timer=setTimeout(()=>controller.abort(),timeout);
    try{
      const response=await fetcher(base+path,{...options,signal:controller.signal,credentials:'omit',redirect:'error'});
      if(!response.ok)throw new Error(`${path} returned HTTP ${response.status}.`);
      const body=await response.text();if(body.length>2000000)throw new Error('API response exceeds the 2 MB display limit.');
      try{return JSON.parse(body);}catch{throw new Error(`${path} did not return valid JSON.`);}
    }catch(error){if(controller.signal.aborted)throw new Error(signal?.aborted?'Connection cancelled.':`${path} timed out.`);throw error;}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
  }
  onProgress('Checking API health…');const health=await request('/health');
  if(!health||typeof health!=='object'||Array.isArray(health))throw new Error('Health endpoint must return a JSON object.');
  onProgress('Loading the scenario reference…');const meta=scenarioMetadata(await request('/demo/scenario?name='+encodeURIComponent(scenarioName)));
  onProgress('Requesting computed analysis…');const result=await request('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(meta.request)});
  return {...adaptGraphResponse(result,meta),api_service:typeof health.service==='string'?health.service:null};
}
