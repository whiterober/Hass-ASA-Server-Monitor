import sys
sys.path.insert(0, '/config')
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP
c = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
print("braces:", c.count("{"), c.count("}"))
print("{0}:", c.count("{0}"))
