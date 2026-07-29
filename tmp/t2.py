import sys
sys.path.insert(0, '/config')
# Force no pyc
sys.dont_write_bytecode = True
import importlib
import build_lovelace
importlib.reload(build_lovelace)
c = build_lovelace.make_ic_css(build_lovelace.SERVER_MAP, build_lovelace.FIXED_STYLES_MAP)
print("braces:", c.count("{"), c.count("}"))
print("{0}:", c.count("{0}"))
# Find first {0}
idx = c.find("{0}")
if idx >= 0:
    # Find the full CSS rule containing it
    start = c.rfind("}", 0, idx)
    end = c.find("}", idx)
    print("Rule:", c[max(0,start-30):end+5])
