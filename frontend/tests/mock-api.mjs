// Frontend-only HTTP harness. Saved graph output and named test variants; no detector runs.
import http from 'node:http';
import {readFile} from 'node:fs/promises';
const ring=JSON.parse(await readFile(new URL('../public/integration/ring.json',import.meta.url),'utf8'));
const normal=JSON.parse(await readFile(new URL('../public/integration/normal.json',import.meta.url),'utf8'));
const allowed=new Set(['http://localhost:4173','http://127.0.0.1:4173']);
http.createServer(async(req,res)=>{
  const origin=req.headers.origin;
  if(origin&&!allowed.has(origin)){res.writeHead(403);res.end();return;}
  const headers={'Content-Type':'application/json','Access-Control-Allow-Origin':origin||'http://localhost:4173','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type','Vary':'Origin'};
  if(req.method==='OPTIONS'){res.writeHead(204,headers);res.end();return;}
  const parts=new URL(req.url,'http://localhost').pathname.split('/').filter(Boolean);
  const variant=['ring','normal','empty','multiple','optional','malformed','invalid-json','unsafe-scenario','unavailable'].includes(parts[0])?parts.shift():'ring';
  const endpoint='/'+parts.join('/');let status=200,body;
  if(variant==='unavailable'){status=503;body={error:'Test-only unavailable API'};}
  else if(req.method==='GET'&&endpoint==='/health')body={status:'ok',service:'frontend-contract-test-harness'};
  else if(req.method==='GET'&&endpoint==='/demo/scenario'){
    body={response_profile:'person3.graph.v2',scenario_id:`test-${variant}`,synthetic:true,analysis_request:{scenario_id:`test-${variant}`}};
    if(variant==='unsafe-scenario')body.analysis_request.customer_rows=[];
  }
  else if(req.method==='POST'&&endpoint==='/analyze'){
    let raw='';for await(const chunk of req){raw+=chunk;if(raw.length>10000){res.writeHead(413,headers);res.end('{}');return;}}
    try{const request=JSON.parse(raw);if(Object.keys(request).length!==1||request.scenario_id!==`test-${variant}`)throw new Error();}
    catch{res.writeHead(400,headers);res.end('{"error":"Expected scenario reference"}');return;}
    body=structuredClone(variant==='normal'?normal.analysis:ring.analysis);
    if(variant==='optional'){delete body.summary.local_risk_score_usage;}
    if(variant==='empty'){body.bank_results=[];body.graph={nodes:[],edges:[]};body.collaborative_alerts=[];body.summary={...body.summary,signals_processed:0,pseudonymous_entities:0,structural_findings:0};body.comparison.local_only={finding_count:0,findings_by_institution:{}};body.comparison.collaborative={finding_count:0,findings:[]};}
    if(variant==='multiple'){body.collaborative_alerts.push({...structuredClone(body.collaborative_alerts[0]),alert_id:'TEST-ONLY-SECOND-CASE'});body.summary.structural_findings=2;body.comparison.collaborative.finding_count=2;body.comparison.collaborative.findings=structuredClone(body.collaborative_alerts);}
    if(variant==='malformed')body.graph.edges[0].source='missing-node';
    if(variant==='invalid-json'){res.writeHead(200,headers);res.end('{broken json');return;}
  }else{status=404;body={error:'Not found'};}
  res.writeHead(status,headers);res.end(JSON.stringify(body));
}).listen(4180,'127.0.0.1',()=>console.log('Frontend contract test harness: http://127.0.0.1:4180/ring'));
