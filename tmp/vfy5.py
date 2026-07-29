import re
c=open("/config/lovelace").read()
tests = [
    ('ig-title-badge:has(.ic-block-img) .ic-qty{position:', 'ig-title base after'),
    ('ig-title-badge:has(.ic-block-img) .ic-qty{padding:', 'ig-title per-color after'),
    ('ic-text:not([class*="ic-block-"]) .ic-qty', 'scoped badge rule'),
    ('ig-item .ic-qty{position:absolute;right:-2px', 'ig-item untouched'),
]
for pat, name in tests:
    n = len(re.findall(re.escape(pat), c))
    print(f'{name}: {n}')
