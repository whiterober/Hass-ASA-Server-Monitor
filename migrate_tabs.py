"""Migrate tabs 1, 2, 4 to table-based mixed_content format."""
import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'asa_tribe_ops.json')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

tabs = data['tabs']

# ---- Tab 1: 无线传送箱速查 (server_list → mixed_content) ----
tab1 = tabs[1]
blocks1 = []
for srv in tab1.get('servers', []):
    rows = []
    for loc in srv.get('locations', []):
        rows.append({
            '地点': loc.get('name', ''),
            '图片': loc.get('image_url', '')
        })
    if rows:
        blocks1.append({
            'block_type': 'table',
            'title': f"{srv['name']}（{srv.get('count', f'{len(rows)}个')}）",
            'columns': ['地点', '图片'],
            'rows': rows
        })
    else:
        blocks1.append({
            'block_type': 'text',
            'style': 'default',
            'text': f"{srv['name']}（{srv.get('count', '0个')}）— 暂无地点数据"
        })

tabs[1] = {
    'id': tab1['id'],
    'name': tab1['name'],
    'description': tab1.get('description', ''),
    'order': tab1.get('order', 2),
    'type': 'mixed_content',
    'content_blocks': blocks1
}

# ---- Tab 2: 泰克套部署速查 (server_list → mixed_content) ----
tab2 = tabs[2]
blocks2 = []
for srv in tab2.get('servers', []):
    rows = []
    for loc in srv.get('locations', []):
        rows.append({
            '地点': loc.get('name', ''),
            '图片': loc.get('image_url', '')
        })
    if rows:
        blocks2.append({
            'block_type': 'table',
            'title': srv['name'],
            'columns': ['地点', '图片'],
            'rows': rows
        })
    else:
        blocks2.append({
            'block_type': 'text',
            'style': 'default',
            'text': f"{srv['name']} — 暂无地点数据"
        })

tabs[2] = {
    'id': tab2['id'],
    'name': tab2['name'],
    'description': tab2.get('description', ''),
    'order': tab2.get('order', 3),
    'type': 'mixed_content',
    'content_blocks': blocks2
}

# ---- Tab 4: 铠护犬功能速查 (mixed_content — text blocks → collapsible notes) ----
tab4 = tabs[4]
for block in tab4.get('content_blocks', []):
    if block.get('block_type') == 'text':
        # Convert warning/danger text blocks to collapsible notes
        block['collapsed'] = True

# Tab 4 stays as mixed_content, no type change

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Migration complete")
print(f"  Tab 1: server_list → mixed_content ({len(blocks1)} blocks)")
print(f"  Tab 2: server_list → mixed_content ({len(blocks2)} blocks)")
print(f"  Tab 4: text blocks → collapsible notes (tables unchanged)")
