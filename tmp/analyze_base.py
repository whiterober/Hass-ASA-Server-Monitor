import json, os

data = json.load(open(r'B:\项目\Hass ASA Server Monitor\bak\asa_20260714_165353\asa_base_quick_ref.json', encoding='utf-8'))
servers = data.get('servers', {})

print('=== 服务器列表 ===')
print(list(servers.keys()))

for sid, sv in servers.items():
    tabs = sv.get('tabs', [])
    print(f'\n{sid}: {len(tabs)} tabs')
    for t in tabs:
        tt = t.get('type', '?')
        sn = t.get('name', '?')
        secs = t.get('sections', [])
        print(f'  [{tt}] {sn} ({len(secs)} sections)')
        if tt == 'raw_html':
            body = t.get('body', '')
            print(f'    body: {len(body)} chars')
            continue
        for sec in secs:
            blocks = sec.get('content_blocks', [])
            sec_name = sec.get('name', '?')
            bts = {}
            for b in blocks:
                bt = b.get('block_type', '?')
                bts[bt] = bts.get(bt, 0) + 1
            print(f'    {sec_name}: {bts}')
