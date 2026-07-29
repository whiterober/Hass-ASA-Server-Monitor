import sys, json
sys.path.insert(0, '/config')
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP
from preview_server import render_tab_html

d = json.load(open('/config/www/asa-data/tribe_ops.json'))
tab = d['tabs'][0]
html = render_tab_html(tab)

# Search for style tag
import re
m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
if m:
    css = m.group(1)
    print("CSS len:", len(css))
    print("Has ic-block-img:", "ic-block-img" in css)
    print("Has ic-qty:", "ic-qty" in css)
    print("Has 30px:", "30px" in css)
    print("Has make_ic output:", "border-radius:12px" in css)
else:
    print("NO STYLE TAG in HTML")
    # Show first 500 chars
    print(html[:500])
