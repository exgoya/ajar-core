import json
from pathlib import Path
from ajar import validate, OWNER

for p in Path('proposals').glob('*.json'):
    plan = validate(json.loads(p.read_text()))
    assert p.stem == plan['slug'], f'Slug mismatch: {p}'
for p in Path('projects').glob('*.json'):
    record = json.loads(p.read_text())
    plan = validate(record['plan'])
    assert p.stem == record['slug'] == plan['slug']
    assert record['owner'] == OWNER
    assert record['repository'] == f"https://github.com/{OWNER}/ajar-{p.stem}"
    assert record['private'] is True
    assert record['status'] in ('planned', 'active', 'paused', 'completed', 'archived')
print('Proposal and project registry validation passed')
