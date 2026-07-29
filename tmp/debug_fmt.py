import sys
sys.path.insert(0, '/config')

# Patch and re-import
import importlib
import build_lovelace

# Let's call make_ic_css with debug
SERVER_MAP = build_lovelace.SERVER_MAP
FIXED_STYLES_MAP = build_lovelace.FIXED_STYLES_MAP

# Manually trace fixed_styles_map
for fk, fv in FIXED_STYLES_MAP.items():
    fc = fv.get('color', '#666')
    if not fc or fc == 'auto': fc = '#666666'
    r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
    _qty_color = 'var(--primary-text-color)' if fk == '_default' else 'var(--primary-background-color)'
    _stroke_col = 'var(--primary-background-color)' if fk == '_default' else 'rgb({},{},{})'.format(r, g, b)
    _qty_color_rule = 'color:'+_qty_color+'!important;' if fk == '_default' else ''
    
    s = 'ha-card .ig-row-wrapper.ic-linear-{0} .ig-title-badge:has(.ic-block-img) .ic-qty,ha-card .ig-row-wrapper.ic-linear-{0} .ig-title-row:has(.ic-block-img) .ic-qty{{'+_qty_color_rule+'padding:1px 5px!important;border-radius:4px 0 0 0!important;font-size:0.8em!important;-webkit-text-stroke:2px {1}!important;paint-order:stroke fill!important}}'
    
    try:
        result = s.format(fk, _stroke_col)
        ok = '{0}' not in result and '{1}' not in result
    except Exception as e:
        ok = False
        result = str(e)
    
    print(f"  {fk}: OK={ok}")

print("Done")
