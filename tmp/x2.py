import json
d = json.load(open('/config/www/asa-data/asa_base_quick_ref.json'))
tab = d['tabs'][0]
print('Tab name:', tab.get('name'))
print('Tab type:', tab.get('type'))
print('Tab keys:', list(tab.keys()))
blocks = tab.get('content_blocks', [])
print('Content blocks:', len(blocks))
for i, b in enumerate(blocks[:5]):
    print(f'  Block {i}: type={b.get("block_type","?")}, keys={list(b.keys())[:8]}')
    if b.get('rows'): print(f'    rows: {len(b["rows"])}')
    if b.get('body'): print(f'    body: {len(b["body"])} chars')
# Check for old server data
if 'servers' in d:
    print('OLD servers key present!')
