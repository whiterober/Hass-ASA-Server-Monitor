import sys
sys.path.insert(0, r'b:\项目\Hass ASA Server Monitor\tmp')
import bl_work_v2 as bl
css = bl.make_ic_css(bl.SERVER_MAP, bl.FIXED_STYLES_MAP)
print('Total len:', len(css))
print('Braces:', css.count('{'), css.count('}'))
print('{0}:', css.count('{0}'))
idx = css.find('ig-title-badge:has(.ic-block-img)')
if idx >= 0:
    end = css.find('}', idx + 100)
    print('First ig-title rule:', css[idx:end+1])
else:
    print('NO ig-title rules!')
