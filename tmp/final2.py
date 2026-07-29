import sys
sys.path.insert(0, '/config')
from build_lovelace import make_ic_css, SERVER_MAP, FIXED_STYLES_MAP

css = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
# Count {0} specifically
c0 = css.count('{0}')
c1 = css.count('{1}')
c2 = css.count('{2}')
print(f"{{0}}: {c0}, {{1}}: {c1}, {{2}}: {c2}")
print(f"Total braces: {{ {css.count('{')} }} {css.count('}')}")

# If {0} found, show first occurrence
if c0 > 0:
    idx = css.index('{0}')
    # Find surrounding CSS rule
    # Go back to start of rule (after })
    start = css.rfind('}', 0, idx)
    if start < 0: start = 0
    else: start += 1
    end = css.find('}', idx)
    print("\nFirst {0} rule:")
    print(css[start:end+1][:300])
