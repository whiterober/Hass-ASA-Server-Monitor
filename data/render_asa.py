#!/usr/bin/env python3
"""ASA Data Renderer — outputs per-tab HTML files with embedded Tailwind CSS."""
import json, sys, os

DATA_DIR = '/config/www/asa-data'

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ============================================================
# EMBEDDED CSS — matches HA's built-in Tailwind + custom classes
# ============================================================
CSS = """<style>
/* === Embedded styles with hardcoded HA dark theme colors === */
/* (CSS variables don't work in iframe — using actual values) */
:root {
  --text: #e0e0e0;
  --text-secondary: #9e9e9e;
  --accent: #4fc3f7;
  --card-bg: #1c1c2e;
  --page-bg: #11111b;
  --border: rgba(128,128,128,0.3);
  --danger: #ef5350;
  --warning: #e6a817;
  --success: #66bb6a;
}
*, *::before, *::after { box-sizing: border-box; }
body { margin:0; padding:8px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       color: #e0e0e0; background: transparent; font-size: 14px; line-height: 1.5; }
.flex { display: flex; }
.flex-col { display: flex; flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.gap-1 { gap: 4px; }
.items-start { align-items: flex-start; }
.justify-center { justify-content: center; }
.w-full { width: 100%; }
.min-w-max { min-width: max-content; }
.h-auto { height: auto; }
.relative { position: relative; }
.absolute { position: absolute; }
.sticky { position: sticky; }
.top-0 { top: 0; }
.left-0 { left: 0; }
.z-10 { z-index: 10; }
.z-20 { z-index: 20; }
.z-30 { z-index: 30; }
.overflow-auto { overflow: auto; }
.table-fixed { table-layout: fixed; }
.border-collapse { border-collapse: collapse; }
.border { border-width: 1px; border-style: solid; }
.border-gray-300 { border-color: rgba(128,128,128,0.3); }
.p-2 { padding: 8px; }
.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mx-0 { margin-left: 0; margin-right: 0; }
.my-4 { margin-top: 16px; margin-bottom: 16px; }
.text-center { text-align: center; }
.text-left { text-align: left; }
.align-top { vertical-align: top; }
.whitespace-nowrap { white-space: nowrap; }
.inline-block { display: inline-block; }
.no-underline { text-decoration: none; }
.rounded-lg { border-radius: 8px; }
.rounded-xl { border-radius: 12px; }
.cursor-pointer { cursor: pointer; }
.font-bold { font-weight: bold; }
.font-semibold { font-weight: 600; }
.transition-opacity { transition: opacity 0.2s; }
.duration-200 { transition-duration: 0.2s; }
.opacity-50 { opacity: 0.5; }
.opacity-100 { opacity: 1; }
.prose { max-width: none; }
.break-all { word-break: break-all; }
.whitespace-pre-line { white-space: pre-line; }
.leading-relaxed { line-height: 1.6; }
.aspect-video { aspect-ratio: 16/9; }
.shadow-sm { box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.object-contain { object-fit: contain; }

/* === HA-specific custom classes === */
.borderr { border-radius: 8px; }
.borderr-top { border-radius: 8px 8px 0 0; }
.borderr-middle { border-radius: 0; }
.borderr-bottom { border-radius: 0 0 8px 8px; }
.borderr-none { border-radius: 0; }

/* Badges */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: 600; color: #fff; }
.badge-sm { font-size: 0.7em; padding: 1px 6px; }
.badge-warning { background: #e6a817; color: #000; }
.badge-info { background: #17a2b8; }
.badge-primary { background: #4fc3f7; color: #000; }
.badge-neutral { background: #6b7280; }

/* Tab bar */
.section-tab-bar { display: flex; gap: 4px; flex-wrap: wrap; padding-bottom: 4px; overflow-x: auto; white-space: nowrap; }
.section-tab { display: inline-block; padding: 8px 16px; border-radius: 8px; cursor: pointer;
    font-size: 0.9em; font-weight: bold; transition: background 0.2s, color 0.2s;
    background: #1c1c2e; color: #e0e0e0;
    user-select: none; }
.section-tab:hover { background: rgba(255,255,255,0.1); }
.section-tab.tab-active { background: #16a34a; color: #fff; }

/* Accordion */
.accordion-body { overflow: hidden; }
.accordion-body.collapsed { display: none; }

/* Table */
table { width: 100%; border-collapse: collapse; }
thead { background: #1c1c2e; }
th { font-weight: 600; background: rgba(0,0,0,0.2); }
tr:hover { background: rgba(255,255,255,0.03); }
code { font-family: "Cascadia Code", "Fira Code", monospace; font-size: 0.85em;
       background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; }
pre { background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; overflow-x: auto; }
pre code { background: none; padding: 0; }
details { margin: 8px 0; }
summary { cursor: pointer; color: #e0e0e0; }

/* Column & row toggle labels (visual only in iframe) */
.col-head { cursor: pointer; user-select: none; }
.row-head { cursor: pointer; user-select: none; }
.col-toggle, .row-toggle { display: none; }

/* Image handling */
img { max-width: 100%; height: auto; border-radius: 4px; }

/* Location chip */
.location-chip { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8em;
    background: rgba(255,255,255,0.1); color: #e0e0e0; margin: 2px; }
.location-chip-wrapper { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
.location-chip-left { background: rgba(79,195,247,0.2); }
.location-chip-badge { font-size: 0.7em; padding: 1px 6px; background: #e6a817; color: #000; border-radius: 8px; }

/* Clamp (collapsible) */
.clamp-wrap { position: relative; }
.clamp-content { max-height: 4.5em; overflow: hidden; transition: max-height 0.3s; }
.clamp-toggle:checked ~ .clamp-content { max-height: none; }
.clamp-btn { display: block; text-align: center; cursor: pointer; color: #e0e0e0; font-size: 0.85em; margin-top: 4px; }
.clamp-btn::after { content: "展开更多 ▼"; }
.clamp-toggle:checked ~ .clamp-btn::after { content: "收起 ▲"; }
.clamp-toggle { display: none; }

/* Highlight dots */
.hl-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin: 0 2px; }
.hl-1 { background: #e6a817; }
.hl-2 { background: #4fc3f7; }
.hl-3 { background: #ef5350; }
.md-hl { font-weight: bold; }
.md-hl-1 { color: #e6a817; }
.md-hl-2 { color: #4fc3f7; }
.md-hl-3 { color: #ef5350; }

/* Map badge */
.map-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }

/* Card grid */
.card-grid { display: grid; gap: 12px; }
.info-card { text-align: center; padding: 12px; border: 1px solid rgba(128,128,128,0.3); border-radius: 8px; background: #1c1c2e; }
.info-card img { width: 60px; height: 60px; object-fit: contain; }
.card-name { font-weight: bold; margin-top: 8px; }
.card-feature { font-size: 0.85em; margin-top: 4px; color: #9e9e9e; }

/* Ha-icon fallback */
ha-icon { display: inline-block; width: 24px; height: 24px; vertical-align: middle; }

/* Text colors */
.text-bold { font-weight: bold; }
.text-green { color: #66bb6a; }
.text-orange { color: #ff9800; }
.text-whiter { color: #fff; }

/* Misc */
.h-divider { border-top: 1px solid rgba(128,128,128,0.2); margin: 8px 0; }
.v-divider { border-left: 1px solid rgba(128,128,128,0.2); margin: 0 8px; }
.tiny-note { font-size: 0.7em; color: #9e9e9e; }
.quote { border-left: 3px solid #e0e0e0; padding-left: 12px; margin: 8px 0; }
.quote-spaced { margin: 16px 0; }
</style>"""

def html_page(title, body):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
{CSS}
</head>
<body>{body}</body>
</html>"""

# ============================================================
# SERVER RULES
# ============================================================
def _server_rules_sections(data):
    sections = data.get('sections', [])
    if not sections:
        return '<p>暂无服务器规则数据。</p>'
    parts = ['<div class="flex flex-col">']
    for s in sections:
        stype = s.get('type',''); title = s.get('title',''); desc = s.get('description','')
        items = s.get('items',[]); footer = s.get('footer_note','')
        parts.append(f'<h3 style="margin:12px 0 4px;color:#e0e0e0">{esc(title)}</h3>')
        if desc: parts.append(f'<p style="margin:0 0 8px;color:#e0e0e0;font-size:0.9em">{esc(desc)}</p>')
        if stype == 'config_list':
            parts.append(f'<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
            for h in ['项目','值','配置文件','代码']: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{h}</th>')
            parts.append('</tr></thead><tbody>')
            for it in items:
                parts.append(f'<tr><td class="border border-gray-300 p-2 text-left align-top">{esc(it.get("icon",""))} {esc(it.get("name",""))}</td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><strong>{esc(it.get("value",""))}</strong></td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><code>{esc(it.get("config_file",""))}</code></td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><code style="color:#4fc3f7">{esc(it.get("config_code",""))}</code></td></tr>')
            parts.append('</tbody></table></div>')
        elif stype == 'toggle_list':
            parts.append(f'<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
            for h in ['状态','项目','配置文件','代码']: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{h}</th>')
            parts.append('</tr></thead><tbody>')
            for it in items:
                icon='✅' if it.get('enabled',True) else '❌'
                parts.append(f'<tr><td class="border border-gray-300 p-2 text-center align-top">{icon}</td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(it.get("name",""))}</td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><code>{esc(it.get("config_file",""))}</code></td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><code style="color:#4fc3f7">{esc(it.get("config_code",""))}</code></td></tr>')
            parts.append('</tbody></table></div>')
        elif stype == 'crafting_list':
            for it in items:
                parts.append(f'<div style="margin:8px 0"><strong style="font-size:1.1em">{esc(it.get("name",""))}</strong></div><ul style="margin:4px 0;padding-left:20px">')
                for ing in it.get('ingredients',[]): parts.append(f'<li>{esc(ing["name"])} ×{ing["count"]}</li>')
                parts.append(f'</ul><details><summary>{esc(it.get("config_file",""))} 代码</summary><pre><code>{esc(it.get("config_code",""))}</code></pre></details>')
        elif stype == 'loot_list':
            parts.append(f'<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
            for h in ['地图','分类','调整','备注']: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{h}</th>')
            parts.append('</tr></thead><tbody>')
            for it in items:
                parts.append(f'<tr><td class="border border-gray-300 p-2 text-left align-top"><strong>【{esc(it.get("map",""))}】</strong></td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(it.get("category",""))}</td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(it.get("adjustment",""))}</td>')
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top"><small>{esc(it.get("note",""))}</small></td></tr>')
            parts.append('</tbody></table></div>')
        if footer: parts.append(f'<p style="color:#9e9e9e;font-size:0.85em;margin-top:4px"><small>{esc(footer)}</small></p>')
    parts.append('</div>')
    return '\n'.join(parts)

# ============================================================
# TRIBE OPS PER-TAB
# ============================================================
def _render_tab(tab):
    ttype = tab.get('type',''); parts = []
    if ttype == 'reference_table':
        cols = tab.get('columns',[]); rows = tab.get('rows',[])
        parts.append(f'<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        for col in cols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>')
            vals = row.values() if isinstance(row, dict) else [row]
            for val in vals: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
    elif ttype == 'server_list':
        for srv in tab.get('servers',[]):
            sname=srv.get('name',''); scount=srv.get('count',''); locs=srv.get('locations',[])
            parts.append(f'<div style="margin:12px 0"><h3 style="margin:0 0 8px">{esc(sname)} <small style="color:#4fc3f7">{esc(scount)}</small></h3>')
            if locs:
                parts.append('<ul style="margin:0;padding-left:20px">')
                for loc in locs:
                    limg=loc.get('image_url','')
                    if limg: parts.append(f'<li style="margin-bottom:4px"><img src="{esc(limg)}" style="max-width:200px;max-height:80px;display:block;margin:4px 0" loading="lazy" />{esc(loc.get("name",""))}</li>')
                    else: parts.append(f'<li>{esc(loc.get("name",""))}</li>')
                parts.append('</ul>')
            else: parts.append('<p style="color:#e0e0e0;font-size:0.85em">暂无地点数据</p>')
            parts.append('</div>')
    elif ttype == 'card_grid':
        cols=tab.get('columns',4); cards=tab.get('cards',[])
        parts.append(f'<div class="card-grid" style="grid-template-columns:repeat({cols},1fr)">')
        for card in cards:
            parts.append(f'<div class="info-card">')
            if card.get('image_url'): parts.append(f'<img src="{esc(card["image_url"])}" loading="lazy" />')
            parts.append(f'<div class="card-name">{esc(card.get("name",""))}</div>')
            if card.get('feature'): parts.append(f'<div class="card-feature">{esc(card["feature"])}</div>')
            parts.append('</div>')
        parts.append('</div>')
    elif ttype == 'mixed_content':
        for block in tab.get('content_blocks',[]):
            bt=block.get('block_type','')
            if bt=='text':
                style = block.get('style','default')
                css = ''
                if style=='warning': css='background:rgba(230,168,23,0.2);border-left:3px solid #e6a817;padding:8px 12px;border-radius:4px'
                elif style=='danger': css='background:rgba(239,83,80,0.2);border-left:3px solid #ef5350;padding:8px 12px;border-radius:4px'
                parts.append(f'<div style="margin:8px 0;{css}">{esc(block.get("text",""))}</div>')
            elif bt=='table':
                if block.get('title'): parts.append(f'<h4 style="margin:12px 0 4px">{esc(block["title"])}</h4>')
                bcols=block.get('columns',[])
                parts.append(f'<div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
                for col in bcols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
                parts.append('</tr></thead><tbody>')
                for row in block.get('rows',[]):
                    parts.append('<tr>')
                    for key,val in row.items():
                        if key.endswith('_icon') and val: parts.append(f'<td class="border border-gray-300 p-2 text-center align-top"><img src="{esc(val)}" style="width:40px;height:40px" /></td>')
                        else: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table></div>')
    elif ttype == 'server_grid':
        columns=tab.get('columns',[]); items=tab.get('items',[])
        parts.append(f'<div class="flex flex-col"><div class="borderr relative overflow-auto border border-gray-300"><table id="supply-table" class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        parts.append(f'<th class="sticky left-0 z-30 border border-gray-300 p-2 text-center whitespace-nowrap">补给品</th>')
        for col in columns:
            parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap"><label class="col-head" title="切换：隐藏该列中的空行"><input type="checkbox" class="col-toggle" hidden /><ha-icon icon="mdi:server"></ha-icon> {esc(col["label"])}</label></th>')
        parts.append('</tr></thead><tbody>')
        for item in items:
            parts.append('<tr>')
            icon_url=item.get('icon_url','')
            parts.append(f'<td class="sticky left-0 z-10 border border-gray-300 p-2 text-center whitespace-nowrap"><label class="row-head"><input type="checkbox" class="row-toggle" hidden />')
            if icon_url: parts.append(f'<img src="{esc(icon_url)}" width="40" height="40" />')
            parts.append('</label></td>')
            for col in columns:
                server_id=col.get('server',''); locs=item.get('locations',{}).get(server_id,[])
                parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">')
                for loc in locs:
                    parts.append(f'{esc(loc.get("name",""))}<br />')
                    if loc.get('image_url'): parts.append(f'<div class="flex flex-wrap gap-1 items-start mb-2"><img src="{esc(loc["image_url"])}" /></div>')
                    badge=loc.get('badge','')
                    if badge: parts.append(f'<span class="badge badge-sm badge-warning mt-1">{esc(badge)}</span>')
                parts.append('</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div></div>')
    elif ttype == 'farming_table':
        cols=tab.get('columns',[]); rows=tab.get('rows',[])
        parts.append(f'<div class="flex flex-col"><div class="borderr relative overflow-auto border border-gray-300"><table class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        for col in cols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>')
            for key,val in row.items():
                if key.endswith('_icon') and val: parts.append(f'<td class="border border-gray-300 p-2 text-center align-top"><img src="{esc(val)}" /></td>')
                else: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div></div>')
    elif ttype == 'raw_html':
        parts.append(tab.get('html',''))
    return '\n'.join(parts)


def _render_base(data):
    servers = data.get('servers',{})
    parts = ['<div class="flex flex-col"><p style="margin:0 0 8px"><strong>已配置基地的服务器：</strong></p><ul style="margin:0;padding-left:20px">']
    for sid, sdata in servers.items():
        if sid!='*' and sdata.get('tabs'):
            parts.append(f'<li style="margin-bottom:4px"><strong>{esc(sdata.get("name",sid))}</strong>: {len(sdata["tabs"])} 个Tab</li>')
    parts.append('</ul><p style="color:#e0e0e0;font-size:0.85em;margin-top:12px"><small>请通过后台编辑器管理基地数据。</small></p></div>')
    return '\n'.join(parts)


# ============================================================
# BATCH RENDER
# ============================================================
RENDERERS = {
    'server_rules.json': ('server_rules.html', lambda d: _server_rules_sections(d)),
    'tribe_ops.json': ('tribe_ops.html', lambda d: None),  # handled specially
    'base_quick_ref.json': ('base_quick_ref.html', lambda d: _render_base(d)),
}

def _render_one(fname, render_func, out_name):
    json_path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(json_path):
        print(f'JSON not found: {json_path}')
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    html = render_func(data)
    out_path = os.path.join(DATA_DIR, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {out_name}: {len(html)} chars')

def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else ['all']

    with open(os.path.join(DATA_DIR, 'server_rules.json'), 'r', encoding='utf-8') as f:
        sr_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'tribe_ops.json'), 'r', encoding='utf-8') as f:
        to_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'base_quick_ref.json'), 'r', encoding='utf-8') as f:
        bq_data = json.load(f)

    print('Rendering:')

    # Server rules
    sr_html = _server_rules_sections(sr_data)
    with open(os.path.join(DATA_DIR, 'server_rules.html'), 'w', encoding='utf-8') as f:
        f.write(html_page('服务器规则', sr_html))
    print(f'  server_rules.html: {len(sr_html)} chars body')

    # Tribe ops: one HTML per tab
    tabs = to_data.get('tabs', [])
    tab_names = []
    for i, tab in enumerate(tabs):
        tab_id = tab.get('id', f'tab_{i}')
        tab_name = tab.get('name', f'Tab {i+1}')
        tab_html = _render_tab(tab)
        full_html = html_page(tab_name, tab_html)
        fn = f'tab_{tab_id}.html'
        with open(os.path.join(DATA_DIR, fn), 'w', encoding='utf-8') as f:
            f.write(full_html)
        tab_names.append((tab_id, tab_name, fn))
        print(f'  {fn}: {len(tab_html)} chars body - {esc(tab_name)}')

    # Base
    bq_html = _render_base(bq_data)
    with open(os.path.join(DATA_DIR, 'base_quick_ref.html'), 'w', encoding='utf-8') as f:
        f.write(html_page('部落基地', bq_html))
    print(f'  base_quick_ref.html: {len(bq_html)} chars body')

    # Also write YAML versions for template sensor !include
    for fn in ['server_rules.html', 'base_quick_ref.html']:
        html_path = os.path.join(DATA_DIR, fn)
        yaml_path = os.path.join(DATA_DIR, fn.replace('.html', '.yaml'))
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        indented = '\n'.join('  ' + line for line in html.split('\n'))
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write('|\n' + indented)

    print(f'\nTotal: server_rules + {len(tabs)} tribe tabs + base')
    print('YAML files updated for template sensors.')

if __name__ == '__main__':
    main()
