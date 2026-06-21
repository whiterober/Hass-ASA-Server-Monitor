import re

val = "var(--md-sys-color-secondary-container-dark, #414659)"
m = re.search(r'var\(--([^,)]+)(?:,\s*([^)]*))?\)', val)
if m:
    print('ref:', repr(m.group(1)))
    print('fallback:', repr(m.group(2)))
else:
    print('NO MATCH')

val2 = "var(--md-sys-color-secondary-container)"
m2 = re.search(r'var\(--([^,)]+)(?:,\s*([^)]*))?\)', val2)
if m2:
    print('ref2:', repr(m2.group(1)))
    print('fallback2:', repr(m2.group(2)))
else:
    print('NO MATCH 2')
