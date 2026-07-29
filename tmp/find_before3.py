src = open(r'B:\项目\Hass ASA Server Monitor\bak\baseline_20260729_155105\build_lovelace.py', encoding='utf-8').read()
for i, line in enumerate(src.split('\n'), 1):
    if 'ic-block-img-before' in line and 'ic-qty' in line:
        print(f'L{i}: {line.strip()[:200]}')
