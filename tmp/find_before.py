src = open(r'b:\项目\Hass ASA Server Monitor\tmp\bl_work_v2.py', encoding='utf-8').read()
idx = src.find('ic-block-img-before')
if idx >= 0:
    # Show all lines mentioning ic-block-img-before
    for i, line in enumerate(src.split('\n'), 1):
        if 'ic-block-img-before' in line and 'ic-qty' in line:
            print(f'L{i}: {line.strip()[:150]}')
else:
    print('NOT FOUND')
