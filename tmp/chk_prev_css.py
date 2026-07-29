import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
# Find the render_tab_html function or CSS injection points
import re
# Search for where CSS/styles are added
for pat in ['make_ic_css', 'IC_CSS', '<style', 'card_mod', 'css +=']:
    for m in re.finditer(pat, src):
        line = src[:m.start()].count('\n') + 1
        ctx = src[m.start():m.start()+150]
        print(f"L{line}: {ctx[:120]}")
    print("---")
