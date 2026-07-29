import sys, json

d = json.load(open(r'B:\项目\Hass ASA Server Monitor\bak\baseline_20260729_174459\server_colors.json', encoding='utf-8'))
server_map = d['servers']
fixed_styles_map = d['presets']

sys.path.insert(0, r'b:\项目\Hass ASA Server Monitor\tmp')
import bl_work_v2 as bl
css = bl.make_ic_css(server_map, fixed_styles_map)

print('Braces:', css.count('{'), css.count('}'))
print('{0}:', css.count('{0}'))
print('ig-title-badge:', css.count('ig-title-badge'))
print('ic-text:not:', css.count('ic-text:not'))

idx = css.find('.ig-title-badge:has(.ic-block-img) .ic-qty{padding:')
if idx >= 0:
    end = css.find('}', idx + 5)
    rule = css[idx:end+1]
    print('Per-color after:', rule[:250])
    print('Has rgb:', 'rgb(' in rule)
