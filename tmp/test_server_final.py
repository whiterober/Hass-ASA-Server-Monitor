import sys
sys.path.insert(0, '/config')
sys.dont_write_bytecode = True
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP
c = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
print('len:', len(c))
print('{0}:', c.count('{0}'))
print('braces:', c.count('{'), c.count('}'))
