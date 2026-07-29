import sys, importlib, os
sys.path.insert(0, '/config')
# Remove any cached .pyc
cached = '/config/__pycache__/build_lovelace.cpython-312.pyc'
if os.path.exists(cached): os.remove(cached)

import build_lovelace
css = build_lovelace.make_ic_css(build_lovelace.SERVER_MAP, build_lovelace.FIXED_STYLES_MAP)

# Check how many rules have {0}
import re
bad_rules = re.findall(r'[^}]ha-card[^{]*\{0\}[^}]*\{[^}]*\}', css)
print(f"Rules with {{0}}: {len(bad_rules)}")
if bad_rules:
    print("First:", bad_rules[0][:200])
