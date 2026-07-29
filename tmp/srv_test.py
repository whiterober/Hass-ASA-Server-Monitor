import sys, json
sys.path.insert(0, '/config')
S = json.load(open('/config/server_colors.json'))
F = json.load(open('/config/www/asa-data/icon_anti_color.json'))
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP
css = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
print("braces:", css.count("{"), css.count("}"))
print("{0}:", css.count("{0}"))
# Find first {0}
idx = css.find("{0}")
if idx >= 0:
    end = css.find("}", idx)
    start = max(0, css.rfind("}", 0, idx))
    print("First {0} rule:", css[start+1:end+1][:200])
