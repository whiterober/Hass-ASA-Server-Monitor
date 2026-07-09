#!/usr/bin/env python3
"""Load sb_labels from JSON and set input_text values via HA REST API."""
import json, urllib.request, urllib.error

LABELS_FILE = '/config/sb_labels.json'
HA_URL = 'http://192.168.199.253:8124'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMjUyYTc2MmQxZDM0ZWU3OTgwNmVlNTgxZjQ4M2E0NCIsImlhdCI6MTc4MzYwODYwNiwiZXhwIjoyMDk4OTY4NjA2fQ.bTdGRM6WP9jvGzu9mJfdFa37jOkIAYoR_HmXnTKPiKw'

HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

labels = {}
try:
    with open(LABELS_FILE) as f:
        labels = json.load(f)
except:
    pass

for n in range(1, 21):
    entity_id = f'input_text.sb_{n}_label'
    value = labels.get(str(n), '')
    data = json.dumps({'state': value}).encode()
    req = urllib.request.Request(
        f'{HA_URL}/api/states/{entity_id}',
        data=data, headers=HEADERS, method='POST'
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f'OK sb_{n}={value[:20]}')
    except Exception as e:
        print(f'ERR sb_{n}: {e}')

print('load done')
