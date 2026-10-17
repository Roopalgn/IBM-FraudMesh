// Explicit mapping of Person 3's corrected component response (34822ed).
// Authored replay uses its separate, explicit fixture validator in model.js.
export const GRAPH_PROFILE='person3.graph.v2';
const fail=m=>{throw new Error(`Graph contract: ${m}`);};
const list=(v,k,max=200)=>Array.isArray(v)&&v.length<=max?v:fail(`${k} must be an array (max ${max}).`);
const text=(v,k)=>typeof v==='string'&&v.trim()&&v.length<=500?v:fail(`${k} must be a nonempty string.`);
const count=(v,k)=>Number.isSafeInteger(v)&&v>=0?v:fail(`${k} must be a nonnegative integer.`);
const score=(v,k)=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1?v:fail(`${k} must be a finite score in [0,1].`);
const strings=(v,k)=>list(v,k).map(x=>text(x,k));
const same=(a,b)=>a.length===b.length&&new Set(a).size===a.length&&a.every(x=>b.includes(x));
const unique=(items,k)=>{if(new Set(items.map(x=>x.id)).size!==items.length)fail(`duplicate ${k}.`);};
const names={bank_a:'Bank A',bank_b:'Bank B',bank_c:'Bank C'};
const titles={cycle:'Directed cycle',cross_institution_cycle:'Cross-institution cycle',cross_institution_structure:'Cross-institution structure',fan_out:'Fan-out',fan_in:'Fan-in',rapid_propagation:'Propagation within coarse hour buckets',ml_informed_priority:'ML-informed review priority'};
const sharedFields=['signal_id','institution_id','source_entity_token','destination_entity_token','timestamp_bucket','amount_bucket','local_risk_score','channel'];
export function adaptGraphResponse(raw,meta){
  if(meta?.profile!==GRAPH_PROFILE)fail(`explicit profile ${GRAPH_PROFILE} required; old response profiles are not guessed.`);
  if(typeof meta.synthetic!=='boolean')fail('synthetic provenance must be explicit.');
  const scenarioId=text(meta.scenario_id,'scenario_id');
  if(raw?.component_metadata?.shared_signal_schema!=='fraudmesh-shared-signal/v1'||raw.component_metadata.scenario!=='synthetic_only'||meta.synthetic!==true)fail('expected corrected synthetic component metadata and shared schema.');
  if(raw.comparison?.comparison_unit!=='structural pattern findings')fail('comparison must explicitly use structural pattern findings.');
  const banks=list(raw.bank_results,'bank_results',3).map(b=>({id:text(b.institution_id,'institution_id'),name:names[b.institution_id]||b.institution_id,
    signals_processed:count(b.signals_processed,'signals_processed'),entity_count:0,local_alerts:null,local_ring_count:null,local_findings:[],local_structural_findings:[]}));
  unique(banks,'institution IDs');const bankIds=new Set(banks.map(b=>b.id));
  const declaredMembership=new Map();
  const nodes=list(raw.graph?.nodes,'graph.nodes',60).map((n,i)=>{
    if(!/^fm1:[0-9a-f]{64}$/.test(n.id))fail('node ID must be a canonical pseudonym.');
    const memberships=strings(n.institution_ids,'institution_ids');if(memberships.some(id=>!bankIds.has(id)))fail('unknown node institution.');
    declaredMembership.set(n.id,memberships);return{id:n.id,label:`Entity ${String(i+1).padStart(2,'0')}`,bank_ids:[],local_risk:null};
  });
  unique(nodes,'node IDs');const nodeMap=new Map(nodes.map(n=>[n.id,n]));
  const edges=list(raw.graph?.edges,'graph.edges').map(e=>{
    if(!nodeMap.has(e.source)||!nodeMap.has(e.target))fail('edge references an unknown node.');
    if(!bankIds.has(e.institution_id))fail('edge references an unknown contributing institution.');
    if(e.id!==e.signal_id)fail('edge id and signal_id disagree.');
    if(!/^\d{4}-\d{2}-\d{2}T\d{2}:00Z$/.test(e.timestamp_bucket)||!Number.isFinite(Date.parse(e.timestamp_bucket)))fail('timestamp must be a UTC hour bucket.');
    if(!['lt_1k','1k_10k','10k_50k','gte_50k'].includes(e.amount_bucket))fail('amount must be a permitted bucket.');
    if(e.channel!==null&&!['transfer','online','card','ach','wire','upi','mobile','atm'].includes(e.channel))fail('invalid channel.');
    for(const id of[e.source,e.target]){const n=nodeMap.get(id);if(!n.bank_ids.includes(e.institution_id))n.bank_ids.push(e.institution_id);}
    return{id:text(e.id,'edge.id'),source:e.source,target:e.target,contributing_bank_id:e.institution_id,kind:e.channel||'relationship',step:0,
      time_bucket:e.timestamp_bucket,amount_bucket:e.amount_bucket,transaction_score:score(e.local_risk_score,'local_risk_score'),risk_band:null};
  });
  unique(edges,'signal IDs');const edgeMap=new Map(edges.map(e=>[e.id,e]));
  for(const n of nodes)if(!same(n.bank_ids,declaredMembership.get(n.id)))fail('node memberships disagree with incident signal contributors.');
  function alert(a,localBank=null){
    const refs=strings(a.linked_entities,'linked_entities'),edgeRefs=strings(a.supporting_signal_ids,'supporting_signal_ids');
    if(new Set(refs).size!==refs.length||new Set(edgeRefs).size!==edgeRefs.length)fail('duplicate evidence references.');
    if(!edgeRefs.length||refs.some(id=>!nodeMap.has(id))||edgeRefs.some(id=>!edgeMap.has(id)))fail('alert references missing graph evidence.');
    const endpoints=[...new Set(edgeRefs.flatMap(id=>[edgeMap.get(id).source,edgeMap.get(id).target]))];
    if(!same(refs,endpoints))fail('case entities disagree with supporting endpoints.');
    const institutions=strings(a.institutions_involved,'institutions_involved'),contributors=[...new Set(edgeRefs.map(id=>edgeMap.get(id).contributing_bank_id))];
    if(!same(institutions,contributors)||typeof a.cross_institution!=='boolean'||a.cross_institution!==(institutions.length>1))fail('case institutions disagree with supporting signals.');
    if(localBank&&(contributors.length!==1||contributors[0]!==localBank))fail('local finding contains another bank’s evidence.');
    if(count(a.edge_count,'edge_count')!==edgeRefs.length)fail('case edge count disagrees with references.');
    const buckets=strings(a.timestamp_buckets,'timestamp_buckets');
    if(!same(buckets,[...new Set(edgeRefs.map(id=>edgeMap.get(id).time_bucket))]))fail('case time buckets disagree with supporting signals.');
    const reasons=list(a.evidence,'evidence',20).map(r=>{
      const code=text(r.code,'reason.code');
      const support=r.supporting_signal_ids===undefined?[]:strings(r.supporting_signal_ids,'reason.supporting_signal_ids');
      if(support.some(id=>!edgeRefs.includes(id)))fail('reason references signal outside its case.');
      if(r.linked_entities!==undefined&&strings(r.linked_entities,'reason.linked_entities').some(id=>!refs.includes(id)))fail('reason references node outside its case.');
      if(r.institutions!==undefined&&strings(r.institutions,'reason.institutions').some(id=>!institutions.includes(id)))fail('reason references institution outside its case.');
      let detail=support.length?`Supporting signals: ${support.join(', ')}.`:'Case-level evidence.';
      if(code==='ml_informed_priority')detail+=` Policy ${text(r.policy_version,'policy_version')}; review priority ${score(r.priority_score,'priority_score').toFixed(3)}; not a fraud probability.`;
      if(code==='rapid_propagation')detail+=` ${count(r.elapsed_minutes,'elapsed_minutes')} minutes between UTC hour buckets; not measured detection latency or exact event timing.`;
      return{code,title:titles[code]||code,detail,edge_ids:support};
    });
    return{id:text(a.alert_id,'alert_id'),title:a.cross_institution?(a.structural_pattern==='cycle'?'Cross-institution cycle':'Cross-institution structure'):`Local ${text(a.structural_pattern,'structural_pattern')}`,
      triage:a.triage===undefined?null:{priority_score:score(a.triage.priority_score,'triage.priority_score'),review_recommended:a.triage.review_recommended===true},severity:text(a.risk_level,'risk_level'),detected_at_step:0,node_ids:refs,edge_ids:edgeRefs,reasons,timestamp_buckets:buckets};
  }
  const alerts=list(raw.collaborative_alerts,'collaborative_alerts',100).map(a=>alert(a));unique(alerts,'alert IDs');
  for(const b of banks){
    b.entity_count=nodes.filter(n=>n.bank_ids.includes(b.id)).length;
    if(edges.filter(e=>e.contributing_bank_id===b.id).length!==b.signals_processed)fail('bank signal count disagrees with graph.');
    const supplied=raw.bank_results.find(x=>x.institution_id===b.id);
    b.local_structural_findings=list(supplied.local_structural_findings,'local_structural_findings').map(a=>alert(a,b.id));unique(b.local_structural_findings,'local finding IDs');
    b.local_ring_count=b.local_structural_findings.length;
    const compared=raw.comparison.local_only?.findings_by_institution?.[b.id];
    if(!Array.isArray(compared)||!same(compared.map(a=>a.alert_id),b.local_structural_findings.map(a=>a.id)))fail('local comparison disagrees with bank findings.');
  }
  if(count(raw.summary?.signals_processed,'summary.signals_processed')!==edges.length||count(raw.summary.pseudonymous_entities,'summary.pseudonymous_entities')!==nodes.length||count(raw.summary.structural_findings,'summary.structural_findings')!==alerts.length)fail('summary counts disagree with graph/cases.');
  if(count(raw.comparison.local_only?.finding_count,'local finding_count')!==banks.reduce((n,b)=>n+b.local_ring_count,0)||count(raw.comparison.collaborative?.finding_count,'combined finding_count')!==alerts.length)fail('comparison counts disagree with findings.');
  if(!same(list(raw.comparison.collaborative.findings,'combined findings').map(a=>a.alert_id),alerts.map(a=>a.id)))fail('combined comparison references disagree.');
  const privacy=raw.privacy;if(!privacy)fail('privacy declarations required.');
  return{schema_version:'display-2',profile:GRAPH_PROFILE,scenario_id:scenarioId,synthetic:meta.synthetic,
    provenance:meta.provenance?Object.fromEntries(['kind','repository','commit','function','networkx_version','input','local_comparison','live_api_verified','linuxone_verified'].filter(k=>Object.hasOwn(meta.provenance,k)).map(k=>[k,meta.provenance[k]])):null,
    review_queue:raw.review_queue?{combined_recommended:count(raw.review_queue.combined_recommended,'combined_recommended'),local_recommended:count(raw.review_queue.local_recommended,'local_recommended'),cross_bank_recommended:count(raw.review_queue.cross_bank_recommended,'cross_bank_recommended')}:null,
    replay_supported:false,banks,graph:{nodes,edges},collaborative_alerts:alerts,comparison:{local_valid:true,note:'Controlled structural findings from the same rules in local and combined views. Transaction-risk flags are separate and unavailable here; these counts are not an accuracy benchmark.'},
    sharing_summary:{raw_rows_shared:null,raw_rows_received:null,shared_fields:sharedFields,retained_local:[],execution_verified:false,
      service_verifies:strings(privacy.service_verifies,'service_verifies'),service_cannot_verify:strings(privacy.service_cannot_verify,'service_cannot_verify'),limitations:strings(privacy.limitations,'limitations'),
      privacy_description:'The component validates permitted signal representations. It does not prove all upstream bank behavior or eliminate inference risk.'},measurement:null};
}
