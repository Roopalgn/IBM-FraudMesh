"""Generate display fixtures with unchanged, pinned Person 3 code. Never export keys/raw rows."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import networkx

parser = argparse.ArgumentParser()
parser.add_argument('--repo', default='.')
parser.add_argument('--ref', default='34822ed09e167a810abc29cdde5104b569e84b72')
args = parser.parse_args()
commit = subprocess.check_output(['git', '-C', args.repo, 'rev-parse', args.ref], text=True).strip()
out = Path(__file__).resolve().parents[1] / 'public' / 'integration'
out.mkdir(parents=True, exist_ok=True)
workspace = Path(args.repo).resolve()
with tempfile.TemporaryDirectory(prefix='.fixture-build-', dir=workspace) as temporary:
    assert Path(temporary).resolve().is_relative_to(workspace)
    package = Path(temporary) / 'fraudmesh'
    package.mkdir()
    hashes = {}
    for name in ['__init__.py', 'privacy.py', 'graph_engine.py', 'integration.py', 'scenarios.py', 'local_transform.py']:
        content = subprocess.check_output(['git', '-C', args.repo, 'show', f'{commit}:fraudmesh/{name}'])
        (package / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    sys.path.insert(0, temporary)
    build = importlib.import_module('fraudmesh.integration').build_analysis_response
    scenarios = importlib.import_module('fraudmesh.scenarios')
    create = importlib.import_module('fraudmesh.privacy').create_shared_signal
    normal = [create(signal_id=f'normal-{i}', institution_id=bank,
        source_entity_id=f'normal-source-{i}', destination_entity_id=f'normal-target-{i}',
        timestamp='2026-10-17T10:00:00Z', amount=150, local_risk_score=.1,
        secret=scenarios.DEMO_SECRET, channel='card')
        for i, bank in enumerate(['bank_a', 'bank_b', 'bank_c'], 1)]
    ring_signals = scenarios.three_bank_fraud_ring()
    local_control = [dict(signal, institution_id='bank_a') for signal in ring_signals]
    inputs = [('ring', ring_signals), ('normal', normal), ('local-control', local_control)]
    descriptions = {'ring': 'three_bank_fraud_ring()', 'normal': 'three disjoint one-edge bank signals',
                    'local-control': 'same three-edge cycle with all signals contributed by bank_a'}
    for name, signals in inputs:
        analysis = build(signals)
        result = {'profile': 'person3.graph.v2', 'scenario_id': f'computed-{name}', 'synthetic': True,
            'provenance': {'kind': 'generated-fixture', 'repository': 'https://github.com/Roopalgn/IBM-FraudMesh',
                'commit': commit, 'function': 'fraudmesh.integration.build_analysis_response',
                'networkx_version': networkx.__version__, 'source_sha256': hashes,
                'input': descriptions[name],
                'local_comparison': 'same structural detector applied per institution and to combined signals',
                'live_api_verified': False, 'linuxone_verified': False},
            'analysis': analysis}
        (out / f'{name}.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f'{name}: {len(analysis["graph"]["nodes"])} entities, {len(analysis["graph"]["edges"])} signals, {len(analysis["collaborative_alerts"])} cases')
