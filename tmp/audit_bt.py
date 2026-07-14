import json, os

d = r'B:\项目\Hass ASA Server Monitor\bak\asa_20260714_165353'
all_bt = set()
ts = []

for fn in ['server_rules.json', 'tribe_ops.json']:
    p = os.path.join(d, fn)
    data = json.load(open(p, encoding='utf-8'))
    for t in data.get('tabs', []):
        bts = {b.get('block_type', '(none)') for b in t.get('content_blocks', [])}
        all_bt |= bts
        ts.append((fn, t.get('name', '?'), t.get('type', '(none)'), bts))

p2 = os.path.join(d, 'asa_base_quick_ref.json')
data2 = json.load(open(p2, encoding='utf-8'))
for sid, sv in data2.get('servers', {}).items():
    for t in sv.get('tabs', []):
        bts = {b.get('block_type', '(none)') for b in t.get('content_blocks', [])}
        all_bt |= bts
        ts.append(('asa_base_quick_ref', f'{sid}:{t.get("name","?")}', t.get('type', '(none)'), bts))

print('=== Tab 清单 ===')
for s, n, tt, bts in ts:
    print(f'  [{s}] {n}  type={tt}  blocks={bts}')

print(f'\n=== 实际 block_type ({len(all_bt)}个) ===')
for bt in sorted(all_bt):
    print(f'  {bt}')
