import sys
sys.path.insert(0, r'b:\项目\Hass ASA Server Monitor\tmp')
import bl_work_v2 as bl
css = bl.make_ic_css(bl.SERVER_MAP, bl.FIXED_STYLES_MAP)
print('braces:', css.count('{'), css.count('}'))
print('{0}:', css.count('{0}'))
print('ig-title base pos:', css.count('ig-title-badge:has(.ic-block-img) .ic-qty{position:'))
print('ig-title per-color:', css.count('ig-title-badge:has(.ic-block-img) .ic-qty{padding:'))
print('scoped badge:', css.count('ic-text:not([class*="ic-block-"])'))
print('ig-item pos:', css.count('ig-item .ic-qty{position:absolute'))
