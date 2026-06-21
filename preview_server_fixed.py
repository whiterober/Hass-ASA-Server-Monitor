"""Server-side preview renderer. Reads theme from HA theme file, renders tabs."""
import sys, json, os, re

sys.path.insert(0, '/config')
from build_lovelace import (
    render_server_grid, render_expandable_detail, render_farming_table, render_tab_html,
    SERVER_GRID_CSS, EXPANDABLE_DETAIL_CSS, FARMING_TABLE_CSS, SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS
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
    with open(os.path.join(DATA_DIR, 'tribe_ops.json'), 'r', encoding='utf-8') as f:
        tribe = json.load(f)

    tabs = tribe.get('tabs', [])
    tab = None
    for t in tabs:
        if t.get('name') == tab_name:
            tab = t; break
    if not tab:
        try: tab = tabs[int(tab_name)]
        except:
            print(f"ERROR: tab '{tab_name}' not found")
            sys.exit(1)

    ttype = tab.get('type', '')
    if ttype == 'mixed_content':
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
            css += 'ha-card .filter-bar button{padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;background:var(--primary-background-color)!important;color:var(--secondary-text-color)!important;font-size:.85em!important;cursor:pointer!important}'
            css += 'ha-card .filter-bar button.active{background:var(--accent-color,#4fc3f7)!important;color:#000!important;border-color:var(--accent-color,#4fc3f7)!important}'
            css += 'ha-card .filter-card{display:none!important}ha-card .filter-card.show{display:flex!important}'
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
            css += 'ha-card .filter-bar button{padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;background:var(--primary-background-color)!important;color:var(--secondary-text-color)!important;font-size:.85em!important;cursor:pointer!important}'
            css += 'ha-card .filter-bar button.active{background:var(--accent-color,#4fc3f7)!important;color:#000!important;border-color:var(--accent-color,#4fc3f7)!important}'
            css += 'ha-card .filter-card{display:none!important}ha-card .filter-card.show{display:flex!important}'
        if 'info_card' in block_types:
            IC_CSS = 'ha-card .info-card-block{border-radius:12px!important;border-left:4px solid!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;align-items:flex-start!important;gap:12px!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Isl]{border-color:#4CAF50!important;background:rgba(76,175,80,.1)!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Sco]{border-color:#FF5722!important;background:rgba(255,87,34,.1)!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Cen]{border-color:#009688!important;background:rgba(0,150,136,.1)!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Abe]{border-color:#9C27B0!important;background:rgba(156,39,176,.1)!important}'
            IC_CSS += 'ha-card .info-card-block[data-map=Ext]{border-color:#00BCD4!important;background:rgba(0,188,212,.1)!important}'
            IC_CSS += 'ha-card .info-card-block .ic-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important;background:rgba(255,255,255,.05)!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body{flex:1!important;min-width:0!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:4px!important}'
            IC_CSS += 'ha-card .info-card-block .ic-body .ic-text{font-size:.9em!important;color:var(--secondary-text-color)!important;line-height:1.5!important}'
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

    full_html = """<!DOCTYPE html>
<html data-theme="dark"><head><meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css" rel="stylesheet"/>
<link href="/local/asa-data/vendor.css" rel="stylesheet"/>
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
