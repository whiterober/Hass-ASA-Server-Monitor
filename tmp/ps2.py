"""Server-side preview renderer. Reads theme from HA theme file, renders tabs."""
import sys, json, os, re

sys.path.insert(0, '/config')
from build_lovelace import (
    render_server_grid, render_expandable_detail, render_farming_table, render_tab_html,
    SERVER_GRID_CSS, EXPANDABLE_DETAIL_CSS, FARMING_TABLE_CSS, SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS, strip_and_append_empty_rows,
    SERVER_MAP, FIXED_STYLES_MAP, _lookup_style
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
                # Robust accordion: use closest() to find parent container,
                # then query within it (works in both Shadow DOM and regular DOM).
                # Fallback to getRootNode() for edge cases.
                onclick_js = (
                    "(function(el){{"
                    "var bar=el.closest('.section-tab-bar');"
                    "var root=bar?bar.parentNode:(el.getRootNode?el.getRootNode():document);"
                    "var bodies=root.querySelectorAll('.accordion-body');"
                    "for(var k=0;k<bodies.length;k++)bodies[k].classList.add('collapsed');"
                    "var cur=root.querySelector('#{sid}-body');if(cur)cur.classList.remove('collapsed');"
                    "var tabs=root.querySelectorAll('.section-tab');"
                    "for(var k=0;k<tabs.length;k++)tabs[k].classList.remove('tab-active');"
                    "el.classList.add('tab-active');"
                    "}})(this)"
                ).format(sid=sid)
                parts.append('<div class="section-tab{}" onclick="{}">{}</div>'.format(active, onclick_js, sec.get('name', '')))
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
                sec_html_list.append('<div id="{}-body" class="accordion-body borderr-none{}">{}</div>'.format(sid, collapsed, '\n'.join(body_parts)))
            parts.extend(sec_html_list)
            html = strip_and_append_empty_rows('\n'.join(parts))
        else:
            html = strip_and_append_empty_rows(tab.get('html', '<p>暂无数据</p>'))
        css = CARD_CORE_CSS + BASE_RAW_CSS
    elif ttype == 'reference_table':
        html = render_tab_html(tab)
        css = CARD_CORE_CSS + TABLE_CORE_CSS
    elif ttype == 'mixed_content':
        # All tabs now use mixed_content with content_blocks
        html = render_tab_html(tab)
        # Compose CSS from block types
        block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
        has_icon_group = any(
            isinstance(d, dict) and d.get('type') == 'icon_group'
            for b in tab.get('content_blocks', [])
            for d in b.get('descriptions', [])
        )
        css = CARD_CORE_CSS

        # === Unconditional image CSS for info_card descriptions ===
        css += 'ha-card .ic-desc-img{width:24px!important;height:24px!important;object-fit:contain!important;vertical-align:middle!important;margin:0 2px!important;flex-shrink:0!important}'
        css += 'ha-card .ic-text[class*="ic-block-"]{position:relative!important;overflow:hidden!important}'
        css += 'ha-card .ic-block-img{position:absolute!important;right:2px!important;top:50%!important;transform:translateY(-50%)!important;width:30px!important;height:30px!important;object-fit:contain!important;border-radius:0 4px 4px 0!important;flex-shrink:0!important}'
        css += 'ha-card .ic-qty{font-size:0.75em!important;font-weight:600!important;margin-left:0!important;flex-shrink:0!important;line-height:1!important}'
        css += 'ha-card .ic-text[class*="ic-block-"] .ic-qty{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-background-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important}'
        css += 'ha-card .ic-text[class*="ic-block-"]:has(.ic-block-img){padding-right:34px!important}'
        for sid, sm in SERVER_MAP.items():
            r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
            css += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(sid, r, g, b, r, g, b)
            css += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(sid, r, g, b)
        for fk, fv in FIXED_STYLES_MAP.items():
            fc = fv.get('color', '#666')
            if not fc or fc == 'auto': fc = '#666666'
            r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
            css += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(fk, r, g, b, r, g, b)
            css += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(fk, r, g, b)
        # === End unconditional image CSS ===
        if block_types & {'server_grid','table','reference_table'}:
            css += TABLE_CORE_CSS
        if 'server_grid' in block_types:
            css = SERVER_GRID_CSS
        if 'expandable_detail' in block_types:
            css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')
        if 'supply_card' in block_types or 'filtered_cards' in block_types or 'map_filter' in block_types:
            css += 'ha-card .supply-card{border-radius:12px!important;border-left:4px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
            css += 'ha-card .supply-card .sc-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important}'
            css += 'ha-card .supply-card .sc-body{flex:1!important;min-width:0!important}'
            css += 'ha-card .supply-card .sc-body .sc-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:6px!important}'
            css += 'ha-card .supply-card .sc-body .sc-servers{display:flex!important;flex-wrap:wrap!important;gap:6px 12px!important}'
            css += 'ha-card .supply-card .sc-body .sc-srv{display:flex!important;align-items:center!important;gap:4px!important;font-size:.85em!important}'
            css += ''
            css += 'ha-card .supply-card .sc-body .sc-srv img{width:20px!important;height:20px!important;object-fit:contain!important;border-radius:2px!important}'
            for sid, sm in SERVER_MAP.items():
                css += 'ha-card .supply-card .sc-srv[data-map={}]{{color:{}!important}}'.format(sid, sm['color'])
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:6px!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;pointer-events:none!important}'
            css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:0!important;margin-bottom:12px!important}'
            css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;width:0!important;height:0!important}'
            css += 'ha-card .filter-label{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;font-size:.85em!important;cursor:pointer!important;user-select:none!important;line-height:1.4!important;white-space:nowrap!important;min-height:28px!important;margin-right:6px!important;margin-bottom:8px!important}'
            for sid, sm in SERVER_MAP.items():
                css += 'ha-card .filter-label[data-map={}]{{background:{}!important;color:var(--primary-background-color)!important;border-color:{}!important}}'.format(sid, sm['color'], sm['color'])
            css += 'ha-card .filter-label{transition:opacity .2s!important}'
            css += 'ha-card .filter-label ha-icon{pointer-events:none!important}'
            css += 'ha-card:has(.filter-radio[value=\"\"]:checked) .filterable{display:flex!important}'
            for sid in SERVER_MAP:
                css += 'ha-card:has(.filter-radio[value="{}"]:checked) .filterable{{display:none!important}}'.format(sid)
                css += 'ha-card:has(.filter-radio[value="{}"]:checked) .filterable[data-filter-maps*={}]{{display:flex!important}}'.format(sid, sid)
        if 'info_card' in block_types:
            IC_CSS = 'ha-card .info-card-block{border-radius:12px!important;border-left:4px solid!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;align-items:flex-start!important;gap:12px!important}'
            for sid, sm in SERVER_MAP.items():
                IC_CSS += 'ha-card .info-card-block[data-map={}]{{border-color:{}!important;background:transparent!important}}'.format(sid, sm['color'])
            IC_CSS += 'ha-card .info-card-block .ic-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important;background:transparent!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body{flex:1!important;min-width:0!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:4px!important;display:flex;align-items:center;gap:4px}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-title ha-icon{flex-shrink:0}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-text{font-size:.9em!important;line-height:1.5!important;word-break:break-all!important;display:flex!important;align-items:center!important;gap:2px!important;flex-wrap:wrap!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-text ha-icon,ha-card .info-card-block .ic-body .ic-text i.mdi{flex-shrink:0!important}'
            IC_CSS += 'ha-card .info-card-block .ic-sum-end{display:none}'
            IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-top{display:none!important}'
            IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-end{display:block!important}'
            IC_CSS += 'ha-card .info-card-block ha-icon.ic-auto-color{color:var(--primary-background-color)!important;fill:var(--primary-text-color)!important}'
            IC_CSS += 'ha-card .info-card-block img.ic-auto-dark{filter:none}'
            IC_CSS += 'ha-card .info-card-block img.ic-auto-light{filter:none}'
            IC_CSS += '[data-theme="dark"] ha-card .info-card-block img.ic-auto-dark{filter:invert(1)}'
            IC_CSS += '[data-theme="light"] ha-card .info-card-block img.ic-auto-light{filter:invert(1)}'
            IC_CSS += 'ha-card .info-card-block img.ic-auto-color{filter:var(--ic-icon-filter,none)}'
            IC_CSS += 'ha-card .ic-desc-img{width:24px!important;height:24px!important;object-fit:contain!important;vertical-align:middle!important;margin:0 2px!important;flex-shrink:0!important}'
            IC_CSS += 'ha-card .ic-text[class*="ic-block-"]{position:relative!important;overflow:hidden!important}'
            IC_CSS += 'ha-card .ic-text[class*="ic-block-"]:has(.ic-block-img){padding-right:34px!important}'
            # [xxx] badge rendering — per-map colors
            # Linear mode: light tint bg + map color text
            for sid, sm in SERVER_MAP.items():
                r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
                IC_CSS += 'ha-card .ic-text.ic-linear-'+sid+' .ic-badge{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important;color:'+sm['color']+'!important}'
            for fk, fv in FIXED_STYLES_MAP.items():
                fc = fv.get('color', '#666')
                if not fc or fc == 'auto': fc = '#666666'
                r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
                IC_CSS += 'ha-card .ic-text.ic-linear-'+fk+' .ic-badge{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important;color:'+fc+'!important}'
            # Default badge (no map): subtle primary color bg, text matches body
            IC_CSS += 'ha-card .ic-badge{display:inline-block!important;padding:1px 6px!important;border-radius:10px!important;font-size:0.75em!important;background:color-mix(in srgb,var(--primary-color) 25%,transparent)!important;color:var(--primary-text-color)!important;line-height:1.5!important}'
            IC_CSS += 'ha-card .ic-badge-num{border-radius:3px!important;display:inline-flex!important;justify-content:center!important;width:16px!important;white-space:nowrap!important}'
            # Block mode: cutout matching page bg (adapts to light/dark theme)
            IC_CSS += 'ha-card .ic-text[class*="ic-block-"] .ic-badge-hollow{background:color-mix(in srgb,var(--primary-background-color) 20%,transparent)!important;color:var(--primary-background-color)!important}'
            # 3-state map filter: linear (icon color) + block (background) per-map — auto-generated from SERVER_MAP
            for sid, sm in SERVER_MAP.items():
                IC_CSS += 'ha-card .ic-linear-{} .mdi,ha-card .ic-linear-{} ha-icon{{color:{}!important}}'.format(sid, sid, sm['color'])
            for sid, sm in SERVER_MAP.items():
                IC_CSS += 'ha-card .ic-text.ic-block-{}{{background:{}!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}}'.format(sid, sm['color'])
            for sid in SERVER_MAP:
                IC_CSS += 'ha-card .ic-text.ic-block-{} .mdi,ha-card .ic-text.ic-block-{} ha-icon{{color:var(--primary-background-color)!important}}'.format(sid, sid)
            # Block-level card light-tint backgrounds (for server_states block=2)
            for sid, sm in SERVER_MAP.items():
                r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
                IC_CSS += 'ha-card .info-card-block.ic-block-{}{{background:rgba({},{},{},0.08)!important}}'.format(sid, r, g, b)
            # Fixed styles: hint + warning (same as build_lovelace.py)
            for fk, fv in FIXED_STYLES_MAP.items():
                fc = fv.get('color', '#666')
                if not fc or fc == 'auto': fc = '#666666'
                IC_CSS += 'ha-card .ic-linear-{} .mdi,ha-card .ic-linear-{} ha-icon{{color:{}!important}}'.format(fk, fk, fc)
                if fk == '_default':
                    IC_CSS += '[data-theme="dark"] ha-card .ic-text.ic-block-_default{background:rgba(255,255,255,0.2)!important;border-radius:6px!important;padding:2px 6px!important;color:#fff!important}'
                    IC_CSS += '[data-theme="light"] ha-card .ic-text.ic-block-_default{background:rgba(0,0,0,0.2)!important;border-radius:6px!important;padding:2px 6px!important;color:#000!important}'
                else:
                    IC_CSS += 'ha-card .ic-text.ic-block-{}{{background:{}!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}}'.format(fk, fc)
                IC_CSS += 'ha-card .ic-text.ic-block-{} .mdi,ha-card .ic-text.ic-block-{} ha-icon{{color:var(--primary-background-color)!important}}'.format(fk, fk)
                if fk != '_default':
                    r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
                    IC_CSS += 'ha-card .info-card-block.ic-block-{}{{background:rgba({},{},{},0.08)!important}}'.format(fk, r, g, b)
            # 3-state map filter: linear (icon color) + block (background) per-map
            for sid, sm in SERVER_MAP.items():
                IC_CSS += 'ha-card .ic-linear-'+sid+' .mdi,ha-card .ic-linear-'+sid+' ha-icon{color:'+sm['color']+'!important}'
            for sid, sm in SERVER_MAP.items():
                IC_CSS += 'ha-card .ic-text.ic-block-'+sid+'{background:'+sm['color']+'!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}'
            for sid in SERVER_MAP:
                IC_CSS += 'ha-card .ic-text.ic-block-'+sid+' .mdi,ha-card .ic-text.ic-block-'+sid+' ha-icon{color:var(--primary-background-color)!important}'
            # Block-level card light-tint backgrounds (for server_states block=2)
            for sid, sm in SERVER_MAP.items():
                r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
                IC_CSS += 'ha-card .info-card-block.ic-block-'+sid+'{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.08)!important}'
            css += IC_CSS
        if has_icon_group:
            css += 'ha-card .ig-title-badge{display:inline-flex!important;align-items:baseline!important;font-size:0.65em!important;padding:2px 6px!important;border-radius:6px!important;background:color-mix(in srgb,var(--primary-color) 15%,transparent)!important;color:var(--primary-text-color)!important;line-height:1!important}'
            css += 'ha-card .ig-badge-text{position:relative!important;top:1px!important}'
            css += 'ha-card .icon-group{gap:8px!important}'
            css += 'ha-card .ig-item{position:relative!important;display:inline-flex!important;flex-shrink:0!important}'
            css += 'ha-card .ig-img{width:28px!important;height:28px!important;object-fit:contain!important;border-radius:4px!important}'
            css += 'ha-card .ig-item .ic-qty{position:absolute!important;right:-2px!important;bottom:-2px!important;font-size:0.65em!important}'
            css += 'ha-card .ig-img.ic-auto-color{color:var(--primary-background-color)!important;fill:var(--primary-text-color)!important}'
            css += 'ha-card .ig-img.ic-auto-dark{filter:none!important}'
            css += 'ha-card .ig-img.ic-auto-light{filter:none!important}'
            css += '[data-theme="dark"] .ig-img.ic-auto-dark{filter:invert(1)!important}'
            css += '[data-theme="light"] .ig-img.ic-auto-light{filter:invert(1)!important}'
            css += 'ha-card .ig-img.ic-auto-color{filter:var(--ic-icon-filter,none)!important}'
            # ig-title-line + ::after separator for icon_group rows
            css += 'ha-card .ig-title-line{border:none!important;margin:0!important;border-top:1px solid var(--primary-text-color)!important;opacity:0.15!important}'
            css += 'ha-card .ig-row-wrapper::after{content:\'\'!important;display:block!important;width:100%!important;border-top:1px solid var(--primary-text-color)!important;opacity:0.15!important;margin-top:6px!important}'
            css += 'ha-card .ig-row-wrapper[class*="ic-linear-"]::after{display:none!important}'
            css += 'ha-card .ig-row-wrapper.ig-empty::after{display:none!important}'
            # ig-row-wrapper linear mode: per-map title badge + separator colors
            for sid, sm in SERVER_MAP.items():
                r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
                css += 'ha-card .ig-row-wrapper.ic-linear-'+sid+' .ig-title-badge{color:'+sm['color']+'!important;background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important}'
                css += 'ha-card .ig-row-wrapper.ic-linear-'+sid+' .ig-title-line{border-top-color:'+sm['color']+'!important;opacity:0.4!important}'
                css += 'ha-card .ig-row-wrapper.ic-linear-'+sid+'::after{border-top-color:'+sm['color']+'!important;opacity:0.4!important}'
        # copy_key button
        css += 'ha-card .ic-copy-key{padding:2px 6px!important;border-radius:6px!important;border:none!important;background:#0288d1!important;color:var(--primary-background-color)!important;cursor:pointer!important;font-size:0.9em!important;font-weight:400!important;line-height:1.5!important;transition:filter 0.2s!important}'
        css += 'ha-card .ic-copy-key:hover{filter:brightness(1.15)!important}'
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

    css += ' ha-card ha-icon{line-height:0!important}'

    # === Image sizing for info_card descriptions (unconditional, safe) ===
    css += 'ha-card .ic-desc-img{width:24px!important;height:24px!important;object-fit:contain!important;vertical-align:middle!important;margin:0 1px!important;flex-shrink:0!important}'
    css += 'ha-card .ic-text[class*="ic-block-"]{position:relative!important;overflow:hidden!important}'
    css += 'ha-card .ic-block-img{position:absolute!important;right:2px!important;top:50%!important;transform:translateY(-50%)!important;width:30px!important;height:30px!important;object-fit:contain!important;border-radius:0 4px 4px 0!important;flex-shrink:0!important}'
    css += 'ha-card .ic-text[class*="ic-block-"]:has(.ic-block-img){padding-right:34px!important}'
    css += 'ha-card .ic-qty{font-size:0.75em!important;font-weight:600!important;margin-left:0!important;flex-shrink:0!important;line-height:1!important}'
    css += 'ha-card .ic-text[class*="ic-block-"] .ic-qty{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-background-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important}'
    for sid, sm in SERVER_MAP.items():
        r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
        css += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(sid, r, g, b, r, g, b)
        css += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(sid, r, g, b)
    for fk, fv in FIXED_STYLES_MAP.items():
        fc = fv.get('color', '#666')
        if not fc or fc == 'auto': fc = '#666666'
        r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
        css += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(fk, r, g, b, r, g, b)
        css += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(fk, r, g, b)

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
    css += 'ha-card div.flex.flex-col>div:not([class]){line-height:1.6!important;margin-top:0!important;margin-bottom:8px!important;color:var(--primary-background-color)!important}'
    css += 'ha-card div.flex.flex-col>details:not([class]){line-height:1.6!important;margin-bottom:8px!important;color:var(--primary-background-color)!important;cursor:pointer!important}'
    css += 'ha-card div.flex.flex-col>details:not([class]) summary{font-weight:600!important;color:var(--primary-background-color)!important;padding:4px 0!important}'
    # === End preview-only typography ===

    full_html = """<!DOCTYPE html>
<html data-theme="dark"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
// Apply theme from URL param on load (for new window opens)
(function(){
  var m = new URLSearchParams(location.search).get('theme');
  if (m) document.documentElement.setAttribute('data-theme', m);
})();
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

// Polyfill: exclusive accordion for <details name="ic-acc">
// Native details[name] exclusive grouping not supported in all mobile browsers.
// This JS fallback ensures only one <details name="ic-acc"> is open at a time.
(function() {
  document.querySelectorAll('details[name="ic-acc"]').forEach(function(d) {
    d.addEventListener('toggle', function() {
      if (!this.open) return;
      document.querySelectorAll('details[name="ic-acc"]').forEach(function(o) {
        if (o !== this) o.open = false;
      }, this);
    });
  });
})();
</script>
</body></html>""" % (ha_font_vars, theme_vars, css, html)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"Preview written: {len(full_html)} bytes, tab={tab.get('name','?')}")

if __name__ == '__main__':
    main()
