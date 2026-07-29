import sys
sys.path.insert(0, '/config')
from build_lovelace import make_ic_css
SERVER_MAP = {}
FIXED_STYLES_MAP = {}
try:
    css = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
    print("OK len:", len(css))
    # Check for key rules
    for k in ["ic-block-img", "ic-qty", "ig-title-badge", "ic-text:not"]:
        print(f"  {k}: {css.count(k)}")
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
