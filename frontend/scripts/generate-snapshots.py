"""Save actual authoritative display responses for explicit offline demonstration."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from fraudmesh.demo import demo_request
from fraudmesh.service import analyze_for_dashboard
output=root/'frontend'/'public'/'computed'
output.mkdir(parents=True,exist_ok=True)
source={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['fraudmesh/demo.py','fraudmesh/service.py','fraudmesh/graph_engine.py','fraudmesh/privacy.py']}
commit=subprocess.check_output(['git','-C',str(root),'log','-1','--format=%H','--','fraudmesh/service.py'],text=True).strip()
for name in ['common','ring','normal','local']:
    request=demo_request(name)
    response=analyze_for_dashboard(request['shared_signals'],request['scenario_id'])
    envelope={'provenance':{'kind':'saved-computed-synthetic','backend_commit':commit,'source_sha256':source,
        'function':'fraudmesh.service.analyze_for_dashboard','scenario':name,
        'timing':'not measured; saved snapshot','deployment':'not established by this artifact'},'analysis':response}
    (output/f'{name}.json').write_text(json.dumps(envelope,indent=2)+'\n',encoding='utf-8')
    print(name,len(response['graph']['edges']),len(response['collaborative_alerts']))
