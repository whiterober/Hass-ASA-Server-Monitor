with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix 1: render template - add onchange after the checked ternary
old1 = "'>引用</label>';"
new1 = "' onchange=\\\"toggleBQControls(this)\\\">引用</label>';"
# This won't work either. Let me just use the unique ending of the input tag
# The BQ input ends with: >引用</label>
# I need to change it to: onchange=\"toggleBQControls(this)\">引用</label>

# Actually, find the exact closing of the input tag before '>引用'
# The input tag ends with either: 'checked' or '' followed by '>引用'
# Find: id=\"brCatBQ... checked>引用 or >引用
import re

# Replace: 'checked>引用' → 'checked onchange="toggleBQControls(this)">引用'
# Replace: ''>引用' → ' onchange="toggleBQControls(this)">引用'

# Replace: '>引用</label>' → ' onchange=\"toggleBQControls(this)\">引用</label>'
# But only for BQ checkboxes. Use two patterns:
# 1. For render template: +'>引用
# 2. For addStorageCat: checked>引用
old_a = "+'>引用</label>';"
new_a = "+' onchange=\\\"toggleBQControls(this)\\\">引用</label>';"
c = c.replace(old_a, new_a)
print('Fix render:', c.count('toggleBQControls'))

old_b = "checked>引用</label>';"
new_b = "checked onchange=\\\"toggleBQControls(this)\\\">引用</label>';"
c = c.replace(old_b, new_b)
print('Fix addStorageCat:', c.count('toggleBQControls'))

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
