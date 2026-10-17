import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const port=Number(process.env.PORT||4173);
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'};
const server=http.createServer(async(req,res)=>{
  try{
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'});res.end();return;}
    const url=new URL(req.url,'http://localhost');
    const relative=decodeURIComponent(url.pathname).replace(/^\/+/, '')||'index.html';
    const target=path.resolve(root,relative);
    if(!target.startsWith(root+path.sep)||relative.split(/[\\/]/).some(p=>p.startsWith('.'))){res.writeHead(403);res.end('Forbidden');return;}
    if(!(await stat(target)).isFile())throw new Error('not a file');
    const body=await readFile(target);res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:body);
  }catch{res.writeHead(404);res.end('Not found');}
});
server.on('error',error=>{console.error(error.message);process.exit(1);});
server.listen(port,'127.0.0.1',()=>console.log(`FraudMesh dashboard: http://127.0.0.1:${port}`));
