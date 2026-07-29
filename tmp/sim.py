import sys, json
sys.path.insert(0, '/config')

d = json.load(open('/config/www/asa-data/tribe_ops.json'))
tab = d['tabs'][0]

# Simulate EXACTLY what preview_server.py main() does
from preview_server import render_tab_html, SERVER_MAP, FIXED_STYLES_MAP, CARD_CORE_CSS, BASE_RAW_CSS, SHARED_CSS
import build_lovelace

ttype = tab.get('type', 'mixed_content')
html = render_tab_html(tab)

block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
css = CARD_CORE_CSS

if block_types & {'server_grid','table','reference_table'}:
    css += "TABLE"
if 'info_card' in block_types:
    IC_CSS = build_lovelace.make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
    css += IC_CSS
    print(f"IC_CSS len: {len(IC_CSS)}, has 30px: {'30px' in IC_CSS}")
    print(f"css total len: {len(css)}, has 30px: {'30px' in css}")

# Now check: is the css actually in the final output?
ha_font_vars = "/* ha_font */"
theme_vars = "/* theme */"
full_html = f"<style>{ha_font_vars}\n{theme_vars}\n{css[:200]}\n</style>"
print("Preview:", "30px" in full_html)
