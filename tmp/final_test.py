import sys
sys.path.insert(0, '/config')
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP

css = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
# Check for unformatted {0}
import re
unformatted = re.findall(r'\{[0-9]\}', css)
print(f"Unformatted placeholders: {len(unformatted)}")
if unformatted:
    for m in re.finditer(r'\{[0-9]\}', css):
        print(f"  at {m.start()}: {css[max(0,m.start()-50):m.end()+100]}")
        if len(unformatted) > 5: break
# Also check brace balance
print(f"Brace balance: {{ {css.count('{')} }} {css.count('}')}")
