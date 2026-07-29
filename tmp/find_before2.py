src = open(r'B:\项目\Hass ASA Server Monitor\bak\build_lovelace_backup_20260729.py', encoding='utf-8').read()
for i, line in enumerate(src.split('\n'), 1):
    if 'ic-block-img-before' in line and 'ic-qty' in line:
        print(f'L{i}: {line.strip()[:150]}')
