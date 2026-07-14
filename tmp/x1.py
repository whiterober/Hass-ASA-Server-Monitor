import json
d = json.load(open('/config/www/asa-data/asa_base_quick_ref.json'))
print('Keys:', list(d.keys()))
tabs = d.get('tabs', [])
print('Tabs count:', len(tabs))
for i, t in enumerate(tabs[:3]):
    print(f'  Tab {i}: name={t.get("name","?")}, type={t.get("type","?")}, sections={len(t.get("sections",[]))}')
if 'servers' in d:
    print('OLD FORMAT: servers present!', list(d['servers'].keys())[:3])
