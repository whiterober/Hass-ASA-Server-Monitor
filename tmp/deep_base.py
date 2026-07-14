import json

data = json.load(open(r'B:\项目\Hass ASA Server Monitor\bak\asa_20260714_165353\asa_base_quick_ref.json', encoding='utf-8'))
sv = data['servers']['Isl']
tab = sv['tabs'][0]  # 英灵殿

for si, sec in enumerate(tab['sections']):
    print(f'\n=== Section {si}: {sec["name"]} ({len(sec["content_blocks"])} blocks) ===')
    for bi, b in enumerate(sec['content_blocks']):
        bt = b.get('block_type','?')
        print(f'  Block {bi}: {bt}')
        if bt == 'base_storage':
            for ri, row in enumerate(b.get('rows',[])):
                cats = row.get('categories',[])
                actions = row.get('actions',[])
                print(f'    Row {ri}: device={row.get("device_name","?")} icon={bool(row.get("device_icon_url"))}')
                print(f'      capacity: {row.get("capacity_main","")}/{row.get("capacity_sub","")}')
                print(f'      actions: {actions}')
                print(f'      categories: {len(cats)}')
                for ci, cat in enumerate(cats[:2]):
                    items = cat.get('items',[])
                    print(f'        Cat {ci}: {cat.get("name","?")} ({len(items)} items) bold={cat.get("bold")} color={cat.get("color")}')
                    for ii, item in enumerate(items[:2]):
                        print(f'          Item {ii}: {item.get("name","?")} icon={bool(item.get("icon_url"))}')
