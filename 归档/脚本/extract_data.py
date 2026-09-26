"""Extract structured data from raw HTML in asa_tribe_ops.json."""
import json, re

with open(r'B:\项目\Hass ASA Server Monitor\data\asa_tribe_ops.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# ---- Extract supply table data ----
supply_html = data['tabs'][5]['html']

# Extract column info
col_matches = re.findall(r'<ha-icon icon="([^"]+)"></ha-icon>\s*([^<]+)', supply_html)
columns = []
server_map = {'孤岛': 'Isl', '核心岛': 'Cen', '焦土': 'Sco', '畸变': 'Abe', '灭绝': 'Ext'}
for icon, label in col_matches:
    label = label.strip()
    server = server_map.get(label, label)
    columns.append({'server': server, 'label': label, 'icon': icon})

print(f'Supply columns: {len(columns)}')
for c in columns:
    print(f'  {c["server"]}: {c["label"]} ({c["icon"]})')

# Extract items from tbody
tbody_match = re.search(r'<tbody>(.*?)</tbody>', supply_html, re.DOTALL)
items = []
if tbody_match:
    tbody = tbody_match.group(1)
    row_matches = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)

    for row_html in row_matches:
        img_match = re.search(r'<img[^>]*src="([^"]+)"', row_html)
        icon_url = img_match.group(1) if img_match else ''

        td_matches = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)

        locations = {}
        for idx, col in enumerate(columns):
            server_id = col['server']
            if idx + 1 < len(td_matches):
                cell = td_matches[idx + 1].strip()
                if not cell:
                    continue

                # Find all images
                imgs = re.findall(r'<img[^>]*src="([^"]+)"', cell)
                # Find all badge spans
                badges = re.findall(r'<span[^>]*class="badge[^"]*"[^>]*>([^<]+)</span>', cell)

                # Extract location names: split by <br />, then clean
                # Replace image/div blocks with markers
                text_only = re.sub(r'<div[^>]*>.*?</div>', '[[IMG_DIV]]', cell, flags=re.DOTALL)
                text_only = re.sub(r'<img[^>]*>', '[[IMG]]', text_only)
                text_only = re.sub(r'<span[^>]*>.*?</span>', '', text_only, flags=re.DOTALL)

                chunks = text_only.split('<br />')
                locs = []
                img_idx = 0
                for chunk in chunks:
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    # Remove remaining HTML tags and markers
                    text = re.sub(r'<[^>]+>', '', chunk).strip()
                    text = text.replace('[[IMG_DIV]]', '').replace('[[IMG]]', '').strip()
                    text = re.sub(r'\s+', ' ', text)
                    if text:
                        loc_entry = {'name': text}
                        if img_idx < len(imgs):
                            loc_entry['image_url'] = imgs[img_idx]
                            img_idx += 1
                        locs.append(loc_entry)

                # Assign badges to location entries (in reverse order, badges are after images)
                # Badges in the HTML appear after their associated image, so match them
                badge_idx = 0
                for loc in reversed(locs):
                    if badge_idx < len(badges):
                        loc['badge'] = badges[badge_idx]
                        badge_idx += 1
                    else:
                        break

                if locs:
                    locations[server_id] = locs

        items.append({'icon_url': icon_url, 'locations': locations})

print(f'Supply items: {len(items)}')
for i, item in enumerate(items[:3]):
    print(f'  Item {i}: icon={item["icon_url"][:60]}...')
    for sid, locs in item['locations'].items():
        for loc in locs:
            print(f'    [{sid}] {loc["name"][:40]}, badge={loc.get("badge","")}')

# ---- Extract farming table data ----
farm_html = data['tabs'][6]['html']

tbody_match2 = re.search(r'<tbody>(.*?)</tbody>', farm_html, re.DOTALL)
rows = []
if tbody_match2:
    tbody2 = tbody_match2.group(1)
    row_matches2 = re.findall(r'<tr>(.*?)</tr>', tbody2, re.DOTALL)

    map_remaining = 0
    spot_remaining = 0

    for row_html in row_matches2:
        tds = re.findall(r'<td([^>]*)>(.*?)</td>', row_html, re.DOTALL)
        row_entry = {}
        td_idx = 0

        # Map cell
        if map_remaining > 0:
            map_remaining -= 1
            row_entry['map'] = None
        elif td_idx < len(tds):
            attrs, content = tds[td_idx]
            rspan = re.search(r'rowspan="(\d+)"', attrs)
            classes = ' '.join(re.findall(r'class="([^"]+)"', attrs))
            dmap = re.search(r'data-map="([^"]+)"', attrs)

            text = re.sub(r'<[^>]+>', '', content).strip()
            text = re.sub(r'\s+', ' ', text)

            entry = {'text': text}
            if rspan:
                entry['rowspan'] = int(rspan.group(1))
                map_remaining = int(rspan.group(1)) - 1
            if 'col-neutral' in classes:
                entry['highlight'] = 'neutral'
            elif dmap:
                entry['highlight'] = dmap.group(1)

            row_entry['map'] = entry
            td_idx += 1
        else:
            row_entry['map'] = {}

        # Spot cell
        if spot_remaining > 0:
            spot_remaining -= 1
            row_entry['spot'] = None
        elif td_idx < len(tds):
            attrs, content = tds[td_idx]
            rspan = re.search(r'rowspan="(\d+)"', attrs)
            classes = ' '.join(re.findall(r'class="([^"]+)"', attrs))
            dmap = re.search(r'data-map="([^"]+)"', attrs)

            text = re.sub(r'<[^>]+>', '', content).strip()
            text = re.sub(r'\s+', ' ', text)

            entry = {'text': text}
            if rspan:
                entry['rowspan'] = int(rspan.group(1))
                spot_remaining = int(rspan.group(1)) - 1
            if 'neutral' in classes:
                entry['highlight'] = 'neutral'
            elif dmap:
                entry['highlight'] = dmap.group(1)

            row_entry['spot'] = entry
            td_idx += 1
        else:
            row_entry['spot'] = {}

        # Output cell
        if td_idx < len(tds):
            attrs, content = tds[td_idx]
            img = re.search(r'<img[^>]*src="([^"]+)"', content)
            row_entry['output'] = {'icon_url': img.group(1)} if img else {}
            td_idx += 1
        else:
            row_entry['output'] = {}

        # Flow cell
        if td_idx < len(tds):
            attrs, content = tds[td_idx]

            # Check for clamp-wrap with ol/li structure
            li_matches = re.findall(r'<li>(.*?)</li>', content, re.DOTALL)
            if li_matches:
                steps = [li.strip() for li in li_matches]
                flow_entry = {'steps': steps}

                # Extract extra non-ol content (md-hl spans, etc.)
                non_ol = re.sub(r'<ol>.*?</ol>', '', content, flags=re.DOTALL)
                # Find md-hl spans
                md_hl_matches = re.findall(r'<span[^>]*class="([^"]*md-hl[^"]*)"[^>]*>([^<]+)</span>', non_ol)
                if md_hl_matches:
                    flow_entry['highlights'] = [{'class': m[0], 'text': m[1]} for m in md_hl_matches]

                # Find plain text outside tags
                plain = re.sub(r'<[^>]+>', ' ', non_ol).strip()
                plain = re.sub(r'\s+', ' ', plain)
                if plain:
                    flow_entry['extra_text'] = plain
            else:
                # Simple text
                text = re.sub(r'<[^>]+>', '', content).strip()
                text = re.sub(r'\s+', ' ', text)
                flow_entry = {'steps': [text]}

            row_entry['flow'] = flow_entry

        rows.append(row_entry)

print(f'\nFarming rows: {len(rows)}')
for i, row in enumerate(rows[:5]):
    m = row.get('map')
    s = row.get('spot')
    o = row.get('output', {})
    f = row.get('flow', {})
    mtext = m['text'][:25] if m else '(omitted)'
    stext = s['text'][:25] if s else '(omitted)'
    print(f'  Row {i}: map={mtext}, spot={stext}, output_img={"yes" if o.get("icon_url") else "no"}, steps={len(f.get("steps",[]))}')

# ---- Update data file ----
data['tabs'][5] = {
    'id': 'supply_consumption',
    'name': '补给速查',
    'description': '建议14天补给一次',
    'order': 6,
    'type': 'server_grid',
    'columns': columns,
    'items': items
}

data['tabs'][6] = {
    'id': 'efficient_farming',
    'name': '采集速查',
    'description': '当前各资源最佳采集流程',
    'order': 7,
    'type': 'farming_table',
    'columns': ['地图', '采集点', '产出', '流程'],
    'rows': rows
}

with open(r'B:\项目\Hass ASA Server Monitor\data\asa_tribe_ops.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('\nData file updated successfully!')
