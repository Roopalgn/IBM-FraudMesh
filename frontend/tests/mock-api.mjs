// Contract test harness only. This is not the team's detector or banking backend.
import http from 'node:http';
import { readFile } from 'node:fs/promises';
const fixture=JSON.parse(await readFile(new URL('../public/scenario.json',import.meta.url),'utf8'));
const allowed=new Set(['http://localhost:4173','http://127.0.0.1:4173']);
http.createServer(async(req,res)=>{
  const origin=req.headers.origin;
  if(origin && !allowed.has(origin)){res.writeHead(403);res.end();return;}
  const headers={'Content-Type':'application/json','Access-Control-Allow-Origin':origin||'http://localhost:4173','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type','Vary':'Origin'};
  if(req.method==='OPTIONS'){res.writeHead(204,headers);res.end();return;}
  let status=200,body;
  if(req.method==='GET'&&req.url==='/health')body={status:'ok',service:'synthetic-contract-harness'};
  else if(req.method==='GET'&&req.url==='/demo/scenario')body={analysis_request:{scenario_id:fixture.scenario_id,synthetic:true}};
  else if(req.method==='POST'&&req.url==='/analyze'){
    let raw='';for await(const chunk of req){raw+=chunk;if(raw.length>10000){res.writeHead(413,headers);res.end('{}');return;}}
    try{const input=JSON.parse(raw);if(input.scenario_id!==fixture.scenario_id||input.synthetic!==true)throw new Error();body=fixture;}
    catch{status=400;body={error:'Expected the synthetic scenario request'};}
  }else{status=404;body={error:'Not found'};}
  res.writeHead(status,headers);res.end(JSON.stringify(body));
}).listen(4180,'127.0.0.1',()=>console.log('Synthetic contract harness: http://127.0.0.1:4180'));
