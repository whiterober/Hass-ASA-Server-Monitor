import sys
sys.path.insert(0, '/config')

# Read the source
src = open('/config/build_lovelace.py').read()

# Find and test the problematic line directly
fk = '_default'
_qty_color_rule = 'color:var(--primary-text-color)!important;'
_stroke_col = 'var(--primary-background-color)'

# Test the EXACT line from the file
s = 'ha-card .ic-text.ic-block-{0} .ic-qty{{position:absolute!important;right:0!important;bottom:0!important;'.format(fk)+_qty_color_rule+'font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important;-webkit-text-stroke:2px '+_stroke_col+'!important;paint-order:stroke fill!important}'
print("Test result {0}:", "{0}" in s)
print("Test braces:", s.count("{"), s.count("}"))
