import sys, importlib
sys.path.insert(0, '/config')
# Force reload
if 'build_lovelace' in sys.modules: del sys.modules['build_lovelace']
import build_lovelace
importlib.reload(build_lovelace)

css = build_lovelace.make_ic_css(build_lovelace.SERVER_MAP, build_lovelace.FIXED_STYLES_MAP)
print(f"{{0}}: {css.count('{0}')}")
print(f"Braces: {{ {css.count('{')} }} {css.count('}')}")
if css.count('{0}') > 0:
    idx = css.index('{0}')
    print("Context:", css[max(0,idx-50):idx+150])
