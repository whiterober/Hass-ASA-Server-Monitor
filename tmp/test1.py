import sys
sys.path.insert(0, r'b:\项目\Hass ASA Server Monitor\bak\baseline_20260729_155105')
import build_lovelace as bl

# Test with just ONE server
test_server = {'Isl': bl.SERVER_MAP['Isl']}
test_fixed = {'_default': bl.FIXED_STYLES_MAP['_default']}

css = bl.make_ic_css(test_server, test_fixed)
print('Braces:', css.count('{'), css.count('}'))
print('{0}:', css.count('{0}'))

# Find first {0}
idx = css.find('{0}')
if idx >= 0:
    # Find surrounding rule
    start = css.rfind('}', 0, idx)
    if start < 0: start = 0
    end = css.find('}', idx)
    print('\nRule with {0}:')
    print(css[max(0,start-50):end+5])
