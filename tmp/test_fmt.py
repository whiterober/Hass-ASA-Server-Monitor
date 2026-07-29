# Test the EXACT format string that's failing
fk = '_default'
_stroke_col = 'var(--primary-background-color)'
_qty_color_rule = 'color:var(--primary-text-color)!important;'

s = 'ha-card .ig-row-wrapper.ic-linear-{0} .ig-title-badge:has(.ic-block-img) .ic-qty,ha-card .ig-row-wrapper.ic-linear-{0} .ig-title-row:has(.ic-block-img) .ic-qty{{'+_qty_color_rule+'padding:1px 5px!important;border-radius:4px 0 0 0!important;font-size:0.8em!important;-webkit-text-stroke:2px {1}!important;paint-order:stroke fill!important}}'
print("INPUT:", s[:120]+"...")
try:
    result = s.format(fk, _stroke_col)
    print("OUTPUT:", result[:200])
    print("Has {0}:", '{0}' in result)
except Exception as e:
    print("ERROR:", e)
