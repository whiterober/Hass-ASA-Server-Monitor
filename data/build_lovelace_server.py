"""Server-side build_lovelace — reads JSON from /config/www/asa-data/, writes to /config/lovelace*.
Deploy this file to /config/build_lovelace.py on the HA server."""
import json, os
from datetime import datetime

DATA_DIR = '/config/www/asa-data'
LOVELACE_PATH = '/config/.storage/lovelace'
LOVELACE_OUT = '/config/lovelace'
LOVELACE_DOT_OUT = '/config/lovelace.lovelace'

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# -------------------------------------------------------
# CSS (same as local build_lovelace.py)
# -------------------------------------------------------
SHARED_CSS = """ha-card {
  box-shadow: none !important;
  padding: 0px !important;
  font-size: var(--paper-font-body1_-_font-size, 14px) !important;
  font-family: var(--paper-font-body1_-_font-family, 'Roboto', sans-serif) !important;
}
ha-card table { border-collapse: collapse !important; table-layout: fixed !important; }
ha-card th, ha-card td { padding: 8px !important; overflow: hidden !important; text-overflow: ellipsis !important; }
ha-card .sticky { position: sticky !important; }
ha-card thead th { z-index: 20 !important; border-top: 0 !important; }
ha-card h2 { font-family: inherit !important; font-weight: bold !important; margin: 0 0 16px 0 !important; color: var(--primary-text-color) !important; line-height: 1.3 !important; }
ha-card img { flex-shrink: 0 !important; }
ha-card .border { border-width: 0px 1px 1px 0px !important; border-color: var(--app-theme-color) !important; }
ha-card tbody td { line-height: 1.4 !important; vertical-align: top !important; font-size: var(--paper-font-body1_-_font-size, 12px) !important; }
ha-card .borderr { border-top-left-radius: 8px !important; border-top-right-radius: 8px !important; border-bottom-left-radius: var(--ha-card-border-radius, 12px) !important; border-bottom-right-radius: var(--ha-card-border-radius, 12px) !important; height: var(--collect-table-height, 82vh) !important; }
"""

SERVER_GRID_CSS = SHARED_CSS
FARMING_TABLE_CSS = SHARED_CSS

# Import CSS from local build — read the full CSS since it's too long to duplicate
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from build_lovelace import SERVER_GRID_CSS as _SGC, FARMING_TABLE_CSS as _FTC, \
        render_server_grid, render_farming_table, render_tab_html, render_server_rules
    SERVER_GRID_CSS = _SGC
    FARMING_TABLE_CSS = _FTC
except ImportError:
    # Fallback: use inline CSS if imports fail (server doesn't have local build_lovelace.py)
    pass

# -------------------------------------------------------
# Render functions (fallback if import fails)
# -------------------------------------------------------
if 'render_server_grid' not in dir():
    def render_server_rules(data):
        sections = data.get('sections', [])
        if not sections: return '<p>暂无服务器规则数据。</p>'
        parts = ['<div class="flex flex-col">']
        for s in sections:
            stype = s.get('type',''); title = s.get('title',''); items = s.get('items',[]); footer = s.get('footer_note','')
            parts.append(f'<h3 style="margin:12px 0 4px">{esc(title)}</h3>')
            if stype in ('config_list','toggle_list'):
                parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
                headers = ['项目','值','配置文件','代码'] if stype == 'config_list' else ['状态','项目','配置文件','代码']
                for h in headers: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{h}</th>')
                parts.append('</tr></thead><tbody>')
                for it in items:
                    parts.append('<tr>')
                    if stype == 'config_list':
                        parts.append(f'<td class="border border-gray-300 p-2">{esc(it.get("icon",""))} {esc(it.get("name",""))}</td>')
                        parts.append(f'<td class="border border-gray-300 p-2"><strong>{esc(it.get("value",""))}</strong></td>')
                    else:
                        icon = '✅' if it.get('enabled',True) else '❌'
                        parts.append(f'<td class="border border-gray-300 p-2 text-center">{icon}</td>')
                        parts.append(f'<td class="border border-gray-300 p-2">{esc(it.get("name",""))}</td>')
                    parts.append(f'<td class="border border-gray-300 p-2"><code>{esc(it.get("config_file",""))}</code></td>')
                    parts.append(f'<td class="border border-gray-300 p-2"><code style="color:var(--primary-color)">{esc(it.get("config_code",""))}</code></td></tr>')
                parts.append('</tbody></table></div>')
            if footer: parts.append(f'<p style="color:var(--secondary-text-color);font-size:0.85em;margin-top:4px"><small>{esc(footer)}</small></p>')
        parts.append('</div>')
        return '\n'.join(parts)

    def render_tab_html(tab):
        ttype = tab.get('type',''); parts = []
        if ttype == 'raw_html': return tab.get('html', '')
        parts.append('<div class="flex flex-col">')
        if ttype == 'reference_table':
            cols = tab.get('columns',[]); rows = tab.get('rows',[])
            parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
            for col in cols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
            parts.append('</tr></thead><tbody>')
            for row in rows:
                parts.append('<tr>')
                vals = row.values() if isinstance(row, dict) else [row]
                for val in vals: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
                parts.append('</tr>')
            parts.append('</tbody></table></div>')
        elif ttype == 'server_grid':
            return render_server_grid(tab)
        elif ttype == 'farming_table':
            return render_farming_table(tab)
        parts.append('</div>')
        return '\n'.join(parts)

    def render_server_grid(tab):
        columns = tab.get('columns', []); items = tab.get('items', [])
        parts = ['<div class="flex flex-col">']
        parts.append('<div class="borderr relative overflow-auto border border-gray-300">')
        parts.append('<table id="supply-table" class="table-fixed border-collapse w-full min-w-max">')
        parts.append('<thead class="sticky top-0 z-20"><tr>')
        parts.append('<th class="sticky left-0 z-30 border border-gray-300 p-2 text-center whitespace-nowrap">补给品</th>')
        for col in columns:
            icon = col.get('icon', 'mdi:server'); label = esc(col.get('label', ''))
            parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap"><label class="col-head" title="切换：隐藏该列中的空行"><input type="checkbox" class="col-toggle" hidden /><ha-icon icon="{icon}"></ha-icon> {label}</label></th>')
        parts.append('</tr></thead><tbody>')
        for item in items:
            parts.append('<tr>')
            icon_url = item.get('icon_url', '')
            parts.append('<td class="sticky left-0 z-10 border border-gray-300 p-2 text-center whitespace-nowrap"><label class="row-head" title="切换：隐藏本行为空的整列"><input type="checkbox" class="row-toggle" hidden />')
            if icon_url: parts.append(f'<img src="{esc(icon_url)}" width="40" height="40" />')
            parts.append('</label></td>')
            for col in columns:
                server_id = col.get('server', ''); locs = item.get('locations', {}).get(server_id, [])
                parts.append('<td class="border border-gray-300 p-2 text-left align-top">')
                if locs:
                    loc_names = []
                    for loc in locs:
                        ln = loc.get('name', ''); img_url = loc.get('image_url', ''); badge = loc.get('badge', '')
                        loc_names.append(esc(ln))
                        if img_url: parts.append(f'<div class="flex flex-wrap gap-1 items-start mb-2"><img src="{esc(img_url)}" /></div>')
                        if badge: parts.append(f'<span class="badge badge-sm badge-warning mt-1">{esc(badge)}</span>')
                    parts.append(' | '.join(loc_names))
                parts.append('</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div></div>')
        return '\n'.join(parts)

    def render_farming_table(tab):
        columns = tab.get('columns', []); rows = tab.get('rows', [])
        parts = ['<div class="flex flex-col">']
        parts.append('<div class="borderr relative overflow-auto border border-gray-300">')
        parts.append('<table class="table-fixed border-collapse w-full min-w-max">')
        parts.append('<thead class="sticky top-0 z-20"><tr>')
        for col in columns: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>')
            for key in ['map', 'spot', 'output', 'flow']:
                data = row.get(key)
                if data is None:
                    continue
                if key == 'output':
                    icon_url = data.get('icon_url', '') if isinstance(data, dict) else ''
                    parts.append(f'<td class="border border-gray-300 p-2 align-top col-output">{f"<img src=\\"{esc(icon_url)}\\" alt=\\"\\" />" if icon_url else ""}</td>')
                elif key == 'flow':
                    steps = data.get('steps', []) if isinstance(data, dict) else []
                    parts.append('<td class="border border-gray-300 p-2 text-left align-top col-flow">')
                    if len(steps) > 1:
                        parts.append('<label class="clamp-wrap"><input type="checkbox" class="clamp-toggle" /><div class="clamp-content"><ol>')
                        for step in steps: parts.append(f'<li>{step}</li>')
                        parts.append('</ol></div><span class="clamp-btn"></span></label>')
                    elif steps:
                        parts.append(esc(steps[0]))
                    parts.append('</td>')
                else:
                    text = data.get('text', '') if isinstance(data, dict) else str(data)
                    rspan = data.get('rowspan') if isinstance(data, dict) else None
                    hl = data.get('highlight', '') if isinstance(data, dict) else ''
                    classes = ['border', 'border-gray-300', 'p-2', 'text-center', 'align-top']
                    if key == 'map': classes.append('col-map')
                    elif key == 'spot': classes.append('col-spot')
                    if hl == 'neutral': classes.append('col-neutral' if key == 'map' else 'neutral')
                    attrs = f' class="{" ".join(classes)}"'
                    if rspan: attrs += f' rowspan="{rspan}"'
                    parts.append(f'<td{attrs}>{esc(text)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div></div>')
        return '\n'.join(parts)

# -------------------------------------------------------
# Card builders
# -------------------------------------------------------
def make_content_card(html_content, tab_type=None):
    if tab_type == 'server_grid':
        css = SERVER_GRID_CSS
    elif tab_type == 'farming_table':
        css = FARMING_TABLE_CSS
    else:
        css = SHARED_CSS

    return {
        "type": "custom:mod-card",
        "card_mod": {"style": "ha-card {\n  box-shadow: none !important;\n}\n"},
        "card": {
            "entity": "",
            "content": html_content,
            "ignore_line_breaks": True,
            "always_update": False,
            "parse_jinja": True,
            "code_editor": "Ace",
            "entities": [],
            "bindings": [],
            "actions": [],
            "plugins": {"daisyui": {"themes": ["dark"]}},
            "debounceChangePeriod": 500,
            "type": "custom:tailwindcss-template-card",
            "card_mod": {"style": css}
        }
    }

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
def build():
    with open(os.path.join(DATA_DIR, 'server_rules.json'), 'r', encoding='utf-8') as f:
        sr_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'tribe_ops.json'), 'r', encoding='utf-8') as f:
        to_data = json.load(f)

    with open(LOVELACE_PATH, 'r', encoding='utf-8') as f:
        lovelace = json.load(f)
    views = lovelace['data']['config']['views']

    # Server rules
    sr_html = render_server_rules(sr_data)
    views[8] = {
        "title": "服务器规则", "path": "asa-server-rules", "theme": "Material You",
        "sections": [{"type": "grid", "cards": [make_content_card(sr_html)], "grid_options": {"columns": "full"}}]
    }

    # Info tribe ops
    tabs = to_data.get('tabs', [])
    tab_cards = []
    for t in tabs:
        tname = t['name']; ttype = t['type']
        if ttype == 'server_grid':
            t_html = render_server_grid(t)
        elif ttype == 'farming_table':
            t_html = render_farming_table(t)
        else:
            t_html = render_tab_html(t)
        cond = {
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": tname}],
            "card": make_content_card(t_html, tab_type=ttype),
            "grid_options": {"columns": 24, "rows": "auto"}
        }
        tab_cards.append(cond)

    ts = datetime.now().strftime('%H:%M:%S')
    info_view = views[6]
    info_view['title'] = f'部落运维速查 SYNC-{ts}'
    info_view.pop('column_span', None)

    # Tab bar (button templates rely on HA runtime — keep simple placeholder structure)
    # The actual tab bar is part of the lovelace configuration; here we preserve the existing one
    # from the current lovelace, only replacing the conditional cards.
    # Find existing tab bar:
    existing_sec = info_view['sections'][0]
    existing_vs = existing_sec['cards'][0]
    existing_stack = existing_vs['cards']
    # Keep tab bar (first card), replace all conditional cards
    new_stack = [existing_stack[0]] + tab_cards  # tab bar + new conditional cards

    info_view['sections'] = [{
        "type": "grid",
        "column_span": 2,
        "cards": [{
            "type": "vertical-stack",
            "grid_options": {"columns": "full"},
            "cards": new_stack
        }]
    }]

    # Write output
    raw = json.dumps(lovelace, ensure_ascii=False, indent=2)
    for path in [LOVELACE_OUT, LOVELACE_DOT_OUT, LOVELACE_PATH]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(raw)
        print(f'Wrote {path}: {len(raw)} bytes')

    print(f'Build complete: {len(tabs)} tabs, timestamp {ts}')

if __name__ == '__main__':
    build()
