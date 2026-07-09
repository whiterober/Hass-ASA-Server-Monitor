#!/usr/bin/env python3
"""Save sb_labels from HA states to JSON."""
import json, urllib.request, urllib.error

LABELS_FILE = '/config/sb_labels.json'
HA_URL = 'http://192.168.199.253:8124'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMjUyYTc2MmQxZDM0ZWU3OTgwNmVlNTgxZjQ4M2E0NCIsImlhdCI6MTc4MzYwODYwNiwiZXhwIjoyMDk4OTY4NjA2fQ.bTdGRM6WP9jvGzu9mJfdFa37jOkIAYoR_HmXnTKPiKw'

HEADERS = {'Authorization': f'Bearer {TOKEN}'}

labels = {}
for n in range(1, 21):
    entity_id = f'input_text.sb_{n}_label'
    req = urllib.request.Request(f'{HA_URL}/api/states/{entity_id}', headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        state = json.loads(resp.read()).get('state', '')
        labels[str(n)] = state
        print(f'sb_{n}: {state[:20]}')
    except Exception as e:
        print(f'ERR sb_{n}: {e}')
        labels[str(n)] = ''

with open(LABELS_FILE, 'w') as f:
    json.dump(labels, f, ensure_ascii=False, indent=2)
print(f'save done: {len(labels)} entries')
