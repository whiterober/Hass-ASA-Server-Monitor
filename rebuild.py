"""Rebuild all features from backup baseline"""
D = bytes([34])
N = bytes([13, 10])

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()
org = len(c)

# This rebuild script applies ALL changes.
# Due to complexity, let me just show what needs to be done.
# The backup is 488KB, the target is ~496KB with all features.

print(f'Backup baseline: {org} bytes, braces: {c.count(b"{")}/{c.count(b"}")}')
print('Features to rebuild:')
print('1. Pill control (cat-col-bq)')
print('2. Color dot + popup (cat-color-dot/popup)')
print('3. B bold in input (cat-bold-btn)')
print('4. cat-merged label/sublabel wrapper')
print('5. .sr-row separator')
print('6. +行 rename')
print('7. .btn-small flex')
print('8. margin-top:4px removal')
print('9. ■/show_marker removal')
print('10. marker_color → border-left-color')
print('11. build_lovelace.py CSS fix')
print()
print('TOO MANY CHANGES - need to rebuild step by step.')
print('Suggest: keep v90 as new baseline (working),')
print('re-apply critical changes one at a time with testing.')
