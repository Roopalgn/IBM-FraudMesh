"""Save actual authoritative display responses for explicit offline demonstration."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from fraudmesh.demo import demo_request
from fraudmesh.analysis import analyze_signals
output=root/'frontend'/'public'/'computed'
output.mkdir(parents=True,exist_ok=True)
source={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['fraudmesh/demo.py','fraudmesh/analysis.py','fraudmesh/graph_engine.py','fraudmesh/triage.py']}
commit=subprocess.check_output(['git','-C',str(root),'log','-1','--all','--format=%H','--','fraudmesh/analysis.py'],text=True).strip()
if not commit:
    raise RuntimeError('Backend source revision is unavailable; fetch its history before generating snapshots.')
for name in ['common','ring','normal','local']:
    request=demo_request(name)
    response=analyze_signals(request['shared_signals'])
    envelope={'profile':'person3.graph.v2','scenario_id':request['scenario_id'],'synthetic':True,'provenance':{'kind':'saved-computed-synthetic','backend_commit':commit,'source_sha256':source,
        'function':'fraudmesh.analysis.analyze_signals','scenario':name,
        'timing':'not measured; saved snapshot','deployment':'not established by this artifact'},'analysis':response}
    (output/f'{name}.json').write_text(json.dumps(envelope,indent=2)+'\n',encoding='utf-8')
    print(name,len(response['graph']['edges']),len(response['collaborative_alerts']))
