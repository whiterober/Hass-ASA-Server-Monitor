import sys
sys.path.insert(0, '/config')
import json
from preview_server import render_tab_html

# Load a tab that has info_card blocks
d = json.load(open('/config/www/asa-data/tribe_ops.json'))
tab = d['tabs'][0]  # 经验获取速查
try:
    html = render_tab_html(tab)
    print("HTML len:", len(html))
    # Check for CSS
    for k in ["ic-block-img{", "ic-qty{", "ig-title-badge"]:
        print(f"  {k}: {html.count(k)}")
    # Check for 30px
    print("  30px:", html.count("30px"))
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
