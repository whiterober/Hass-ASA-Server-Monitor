"""Server-side preview renderer. Reads theme from HA theme file, renders tabs."""
import sys, json, os, re

sys.path.insert(0, '/config')
from build_lovelace import (
    render_server_grid, render_expandable_detail, render_farming_table, render_tab_html,
    SERVER_GRID_CSS, EXPANDABLE_DETAIL_CSS, FARMING_TABLE_CSS, SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS
)

DATA_DIR = '/config/www/asa-data'
OUTPUT = '/config/www/preview_tab.html'
THEME_FILE = '/config/themes/material_you/material_you.yaml'

def parse_theme_yaml(path):
    """Parse HA theme YAML and return resolved CSS variable dicts for dark and light modes."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    raw_global = {}
    raw_dark = {}
    raw_light = {}
    section = None  # None=global, 'dark', 'light'
    section_indent = 999
    first_line = True

    for line in content.split('\n'):
        stripped = line.strip()

        if not stripped or stripped.startswith('#'):
            continue
        if first_line and ':' in stripped and not stripped.startswith(' '):
            first_line = False
            continue
        first_line = False
        if stripped == 'modes:':
            continue
        if ':' not in stripped:
            continue

        leading = len(line) - len(line.lstrip())

        if stripped == 'dark:':
            section = 'dark'
            section_indent = leading
            continue
        if stripped == 'light:':
            section = 'light'
            section_indent = leading
            continue

        if section is not None and leading <= section_indent:
            section = None

        idx = stripped.find(':')
        key = stripped[:idx].strip()
        value = stripped[idx+1:].strip()

        if key in ('dark','light'):
            continue

        comment_idx = value.find(' #')
        if comment_idx > 0 and not ("'" in value[:comment_idx] or '"' in value[:comment_idx]):
            value = value[:comment_idx].strip()

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        if section == 'dark':
            raw_dark[key] = value
        elif section == 'light':
            raw_light[key] = value
        else:
            raw_global[key] = value

    # Build final raw dict for each mode (global + mode override)
    def build_raw(mode_raw):
        merged = dict(raw_global)
        merged.update(mode_raw)
        return merged

    # Resolve var() references recursively
    def resolve_dict(raw):
        def resolve_value(value, visited=None):
            if visited is None:
                visited = set()
            m = re.search(r'var\(--([^,)]+)(?:,\s*([^)]*))?\)', value)
            if not m:
                return value
            ref = m.group(1)
            fallback = m.group(2)
            full_match = m.group(0)

            if ref in visited:
                return value.replace(full_match, fallback if fallback else '')

            if ref in raw:
                replacement = resolve_value(raw[ref], visited | {ref})
                return value.replace(full_match, replacement)

            if fallback is not None:
                return value.replace(full_match, fallback)

            return value

        resolved = {}
        for key, value in raw.items():
            prev = None
            while value != prev:
                prev = value
                value = resolve_value(value)
            resolved[key] = value
        return resolved

    raw_merged_dark = build_raw(raw_dark)
    raw_merged_light = build_raw(raw_light)

    return {
        'dark': resolve_dict(raw_merged_dark),
        'light': resolve_dict(raw_merged_light)
    }

def ha_to_mdi(html):
    """Convert <ha-icon icon="mdi:xxx"> to <i class="mdi mdi-xxx">."""
    def replace_icon(m):
        icon = m.group(1).replace(':', '-')
        return f'<i class="mdi {icon}"></i>'
    return re.sub(r'<ha-icon icon="([^"]+)"></ha-icon>', replace_icon, html)

def main():
    tab_name = sys.argv[1] if len(sys.argv) > 1 else ''
    source = sys.argv[2] if len(sys.argv) > 2 else 'tribe_ops'

    # Map source to data file
    file_map = {'tribe_ops': 'tribe_ops.json', 'server_rules': 'server_rules.json', 'base_quick_ref': 'asa_base_quick_ref.json'}
    data_file = file_map.get(source, 'tribe_ops.json')
    with open(os.path.join(DATA_DIR, data_file), 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle base_quick_ref format (servers) vs standard format (tabs)
    if source == 'base_quick_ref':
        # tab_name format: "server_id:tab_index" e.g. "Isl:0"
        parts = tab_name.split(':', 1)
        server_id = parts[0] if len(parts) > 0 else 'Isl'
        tab_idx = int(parts[1]) if len(parts) > 1 else 0
        servers = data.get('servers', {})
        server = servers.get(server_id, {})
        server_tabs = server.get('tabs', [])
        tab = server_tabs[tab_idx] if tab_idx < len(server_tabs) else None
        if not tab:
            print(f"ERROR: server '{server_id}' tab {tab_idx} not found")
            sys.exit(1)
    else:
        tabs = data.get('tabs', [])
        tab = None
        for t in tabs:
            if t.get('name') == tab_name:
                tab = t; break
        if not tab:
            try: tab = tabs[int(tab_name)]
            except:
                print(f"ERROR: tab '{tab_name}' not found in {data_file}")
                sys.exit(1)

    ttype = tab.get('type', '')
    if ttype == 'raw_html':
        # If tab has sections, generate section HTML
        sections = tab.get('sections', [])
        if sections:
            parts = []
            # Section tab bar
            parts.append('<div class="section-tab-bar base-title-header">')
            for i, sec in enumerate(sections):
                active = ' tab-active' if i == 0 else ''
                sid = 'section-' + str(i)
                parts.append('<div class="section-tab{}" onclick="(function(el){{var root=el.getRootNode?el.getRootNode():document;'.format(active))
                for j, s in enumerate(sections):
                    sj = 'section-' + str(j)
                    if j != i:
                        parts.append("root.querySelector('#{}-body').classList.add('collapsed');".format(sj))
                parts.append("root.querySelector('#{}-body').classList.remove('collapsed');".format(sid))
                parts.append("root.querySelectorAll('.section-tab').forEach(function(t){{t.classList.remove('tab-active')}});el.classList.add('tab-active');")
                parts.append('}})(this)">{}</div>'.format(sec.get('name', '')))
            parts.append('</div>')
            # Section bodies
            sec_html_list = []
            for i, sec in enumerate(sections):
                sid = 'section-' + str(i)
                collapsed = '' if i == 0 else ' collapsed'
                body_parts = []
                for b in sec.get('content_blocks', []):
                    bt = b.get('block_type', '')
                    # Generate body from structured data, or fallback to body
                    if b.get('body'):
                        body_parts.append(b['body'])
                    elif bt == 'base_storage' and b.get('rows'):
                        rows_html = []
                        for row in b['rows']:
                            cap = str(row.get('capacity_main',''))+'<sub>'+str(row.get('capacity_sub',''))+'</sub>'
                            icon = '<img src=\"'+row.get('device_icon_url','')+'\" alt=\"'+row.get('device_name','')+'\" />' if row.get('device_icon_url') else ''
                            rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\"></td></tr>')
                        body_parts.append('<table id=\"base-table\" class=\"table-fixed border-collapse w-full min-w-max\"><thead><tr><th class=\"border border-gray-300 p-2\">设备</th><th class=\"border border-gray-300 p-2\" colspan=\"2\">存储</th></tr></thead><tbody>'+''.join(rows_html)+'</tbody></table>')
                sec_html_list.append('<div id="{}-body" class="accordion-body{}">{}</div>'.format(sid, collapsed, '\n'.join(body_parts)))
            parts.extend(sec_html_list)
            html = '\n'.join(parts)
        else:
            html = tab.get('html', '<p>暂无数据</p>')
        css = CARD_CORE_CSS + BASE_RAW_CSS
    elif ttype == 'reference_table':
        html = render_tab_html(tab)
        css = CARD_CORE_CSS + TABLE_CORE_CSS
    elif ttype == 'mixed_content':
        # All tabs now use mixed_content with content_blocks
        html = render_tab_html(tab)
        # Compose CSS from block types
        block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
        css = CARD_CORE_CSS
        if block_types & {'server_grid','table','reference_table'}:
            css += TABLE_CORE_CSS
        if 'server_grid' in block_types:
            css = SERVER_GRID_CSS
        if 'expandable_detail' in block_types:
            css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')
        if 'supply_card' in block_types or 'filtered_cards' in block_types:
            css += 'ha-card .supply-card{border-radius:12px!important;border-left:4px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
            css += 'ha-card .supply-card .sc-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important}'
            css += 'ha-card .supply-card .sc-body{flex:1!important;min-width:0!important}'
            css += 'ha-card .supply-card .sc-body .sc-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:6px!important}'
            css += 'ha-card .supply-card .sc-body .sc-servers{display:flex!important;flex-wrap:wrap!important;gap:6px 12px!important}'
            css += 'ha-card .supply-card .sc-body .sc-srv{display:flex!important;align-items:center!important;gap:4px!important;font-size:.85em!important}'
            css += ''
            css += 'ha-card .supply-card .sc-body .sc-srv img{width:20px!important;height:20px!important;object-fit:contain!important;border-radius:2px!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Isl]{color:#4CAF50!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Sco]{color:#FF5722!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Cen]{color:#009688!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Abe]{color:#9C27B0!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Ext]{color:#00BCD4!important}'
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:6px!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;pointer-events:none!important}'
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:0!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;width:0!important;height:0!important}'
            css += 'ha-card .filter-label{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;font-size:.85em!important;cursor:pointer!important;user-select:none!important;line-height:1.4!important;white-space:nowrap!important;min-height:28px!important;margin-right:6px!important}'
            css += 'ha-card .filter-label[data-map=Isl]{background:#4CAF50!important;color:#fff!important;border-color:#4CAF50!important}'
            css += 'ha-card .filter-label[data-map=Sco]{background:#FF5722!important;color:#fff!important;border-color:#FF5722!important}'
            css += 'ha-card .filter-label[data-map=Cen]{background:#009688!important;color:#fff!important;border-color:#009688!important}'
            css += 'ha-card .filter-label[data-map=Abe]{background:#9C27B0!important;color:#fff!important;border-color:#9C27B0!important}'
            css += 'ha-card .filter-label[data-map=Ext]{background:#00BCD4!important;color:#fff!important;border-color:#00BCD4!important}'
            css += 'ha-card .filter-label.active{box-shadow:0 0 0 2px var(--primary-text-color)!important}'
            css += 'ha-card .filter-label ha-icon{pointer-events:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"\"]:checked) .filterable{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable[data-filter-maps*=Isl]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable[data-filter-maps*=Sco]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable[data-filter-maps*=Cen]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable[data-filter-maps*=Abe]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable[data-filter-maps*=Ext]{display:flex!important}'
        if 'supply_card' in block_types or 'filtered_cards' in block_types:
            css += 'ha-card .supply-card{border-radius:12px!important;border-left:4px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
            css += 'ha-card .supply-card .sc-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important}'
            css += 'ha-card .supply-card .sc-body{flex:1!important;min-width:0!important}'
            css += 'ha-card .supply-card .sc-body .sc-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:6px!important}'
            css += 'ha-card .supply-card .sc-body .sc-servers{display:flex!important;flex-wrap:wrap!important;gap:6px 12px!important}'
            css += 'ha-card .supply-card .sc-body .sc-srv{display:flex!important;align-items:center!important;gap:4px!important;font-size:.85em!important}'
            css += ''
            css += 'ha-card .supply-card .sc-body .sc-srv img{width:20px!important;height:20px!important;object-fit:contain!important;border-radius:2px!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Isl]{color:#4CAF50!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Sco]{color:#FF5722!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Cen]{color:#009688!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Abe]{color:#9C27B0!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Ext]{color:#00BCD4!important}'
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:6px!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;pointer-events:none!important}'
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:0!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;width:0!important;height:0!important}'
            css += 'ha-card .filter-label{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;font-size:.85em!important;cursor:pointer!important;user-select:none!important;line-height:1.4!important;white-space:nowrap!important;min-height:28px!important;margin-right:6px!important}'
            css += 'ha-card .filter-label[data-map=Isl]{background:#4CAF50!important;color:#fff!important;border-color:#4CAF50!important}'
            css += 'ha-card .filter-label[data-map=Sco]{background:#FF5722!important;color:#fff!important;border-color:#FF5722!important}'
            css += 'ha-card .filter-label[data-map=Cen]{background:#009688!important;color:#fff!important;border-color:#009688!important}'
            css += 'ha-card .filter-label[data-map=Abe]{background:#9C27B0!important;color:#fff!important;border-color:#9C27B0!important}'
            css += 'ha-card .filter-label[data-map=Ext]{background:#00BCD4!important;color:#fff!important;border-color:#00BCD4!important}'
            css += 'ha-card .filter-label.active{box-shadow:0 0 0 2px var(--primary-text-color)!important}'
            css += 'ha-card .filter-label ha-icon{pointer-events:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"\"]:checked) .filterable{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable[data-filter-maps*=Isl]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable[data-filter-maps*=Sco]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable[data-filter-maps*=Cen]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable[data-filter-maps*=Abe]{display:flex!important}'
            css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable{display:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable[data-filter-maps*=Ext]{display:flex!important}'
        if 'info_card' in block_types:
            IC_CSS = 'ha-card .info-card-block{border-radius:12px!important;border-left:4px solid!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;align-items:flex-start!important;gap:12px!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Isl]{border-color:#4CAF50!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Sco]{border-color:#FF5722!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Cen]{border-color:#009688!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Abe]{border-color:#9C27B0!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Ext]{border-color:#00BCD4!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block .ic-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body{flex:1!important;min-width:0!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:4px!important;display:flex;align-items:center;gap:4px}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-title ha-icon{flex-shrink:0}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-text{font-size:.9em!important;line-height:1.5!important}'
            IC_CSS += 'ha-card .info-card-block ha-icon.ic-auto-color{color:var(--primary-text-color)!important;fill:var(--primary-text-color)!important}'
            IC_CSS += 'ha-card .info-card-block img.ic-auto-color{filter:var(--ic-icon-filter,none)}'
            css += IC_CSS
        if 'card_grid' in block_types:
            css += 'ha-card .info-card{background:var(--primary-background-color);border-radius:8px;overflow:hidden;text-align:center;padding:0 0 8px 0}ha-card .info-card img{width:100%;aspect-ratio:1;object-fit:cover}ha-card .card-name{font-weight:600;margin:4px 0}ha-card .card-feature{font-size:0.85em;color:var(--secondary-text-color)}ha-card .card-grid{display:grid;gap:12px}'
    elif ttype == 'server_grid':
        html = render_server_grid(tab); css = SERVER_GRID_CSS
    elif ttype == 'expandable_detail':
        html = render_expandable_detail(tab); css = EXPANDABLE_DETAIL_CSS
    elif ttype == 'farming_table':
        html = render_farming_table(tab); css = FARMING_TABLE_CSS
    elif ttype in ('reference_table',):
        html = render_tab_html(tab); css = CARD_CORE_CSS + TABLE_CORE_CSS
    else:
        html = render_tab_html(tab); css = CARD_CORE_CSS

    # Keep <ha-icon> elements as-is — polyfilled by JS in the browser

    # HA platform font-scale defaults (injected by HA frontend, not in theme files)
    ha_font_vars = (
        ':root{--ha-font-size-xl:14px;--ha-font-size-l:12.25px;'
        '--ha-font-size-m:10.5px;--ha-font-size-s:8.75px;'
        'font-size:var(--ha-font-size-xl)}'
    )

    # Load theme from HA theme file (dark + light modes)
    theme_vars = ''
    try:
        both = parse_theme_yaml(THEME_FILE)
        # Dark mode as :root (default)
        dark = both.get('dark', {})
        theme_vars = ':root {\n'
        for key, value in dark.items():
            theme_vars += f'  --{key}: {value};\n'
        theme_vars += '}\n'
        # Light mode under [data-theme="light"]
        light = both.get('light', {})
        theme_vars += '[data-theme="light"] {\n'
        for key, value in light.items():
            theme_vars += f'  --{key}: {value};\n'
        theme_vars += '}\n'
    except Exception as e:
        print(f"Theme load error: {e}")

    # === Preview-only typography fix ===
    # Text blocks render as bare <div>/<details> with no CSS class (unlike other block types
    # which all have classed wrappers). On the actual HA page, daisyui inside
    # custom:tailwindcss-template-card provides typography defaults.
    # The preview has no daisyui, so we add equivalent typography for unclassed elements.
    css += 'ha-card div.flex.flex-col>div:not([class]){line-height:1.6!important;margin-bottom:8px!important;color:var(--primary-text-color)!important}'
    css += 'ha-card div.flex.flex-col>details:not([class]){line-height:1.6!important;margin-bottom:8px!important;color:var(--primary-text-color)!important;cursor:pointer!important}'
    css += 'ha-card div.flex.flex-col>details:not([class]) summary{font-weight:600!important;color:var(--primary-text-color)!important;padding:4px 0!important}'
    # === End preview-only typography ===

    full_html = """<!DOCTYPE html>
<html data-theme="dark"><head><meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css" rel="stylesheet"/>
<link href="/local/asa-data/vendor.css" rel="stylesheet"/>
<link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.23/dist/full.css" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={}</script>
<style>
%s
%s
%s
</style>
</head><body style="background:var(--lovelace-background,var(--primary-background-color));color:var(--primary-text-color);padding:10px;margin:0">
<ha-card>%s</ha-card>
<script>
// Listen for theme changes from parent (asa-admin.html)
window.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'set-theme') {
    document.documentElement.setAttribute('data-theme', e.data.theme);
  }
});

// Polyfill <ha-icon icon="mdi:xxx"> → SVG via MDI CDN (matches HA's shadow DOM structure)
(function() {
  var icons = document.querySelectorAll('ha-icon');
  var mdiBase = 'https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg/';
  icons.forEach(function(el) {
    var icon = el.getAttribute('icon');
    if (!icon || icon.indexOf('mdi:') !== 0) return;
    var name = icon.slice(4);
    fetch(mdiBase + name + '.svg')
      .then(function(r) { return r.ok ? r.text() : Promise.reject(r.status); })
      .then(function(svgText) {
        var match = svgText.match(/<svg[^>]*>([\\s\\S]*)<\\/svg>/);
        var inner = match ? match[1] : '';
        if (!el.shadowRoot) el.attachShadow({mode: 'open'});
        el.shadowRoot.innerHTML = '<style>ha-svg-icon{display:var(--ha-icon-display,inline-flex);align-items:center;justify-content:center;position:relative;vertical-align:middle;fill:var(--icon-primary-color,currentcolor);width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)}ha-svg-icon svg{display:block;width:100%%;height:100%%}</style><ha-svg-icon><svg viewBox=\"0 0 24 24\" preserveAspectRatio=\"xMidYMid meet\" focusable=\"false\" role=\"img\" aria-hidden=\"true\">' + inner + '</svg></ha-svg-icon>';
      })
      .catch(function() { el.textContent = icon; });
  });
})();
</script>
</body></html>""" % (ha_font_vars, theme_vars, css, html)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"Preview written: {len(full_html)} bytes, tab={tab.get('name','?')}")

if __name__ == '__main__':
    main()
