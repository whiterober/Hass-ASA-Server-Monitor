import sys, json, io
sys.path.insert(0, '/config')
from preview_server import render_tab_html

d = json.load(open('/config/www/asa-data/tribe_ops.json'))
tab = d['tabs'][0]

# Now run the FULL main logic
import preview_server as ps
# Capture stdout
old_stdout = sys.stdout
sys.stdout = io.StringIO()

# Simulate main but capture
from preview_server import SERVER_MAP, FIXED_STYLES_MAP, CARD_CORE_CSS, BASE_RAW_CSS, SHARED_CSS

ttype = tab.get('type', 'mixed_content')
html_body = render_tab_html(tab)

block_types = set()
for b in tab.get('content_blocks', []):
    bt = b.get('block_type', 'text')
    block_types.add(bt)
    if bt == 'info_card':
        for d in b.get('descriptions', []):
            block_types.add(d.get('type', 'desc_row'))

css = CARD_CORE_CSS + BASE_RAW_CSS

if ttype == 'mixed_content':
    css += SHARED_CSS
    if 'info_card' in block_types:
        IC_CSS = ps.build_lovelace.make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
        css += IC_CSS

print("CSS len:", len(css))
print("ic-block-img in CSS:", "ic-block-img" in css)
print("30px in CSS:", "30px" in css)
