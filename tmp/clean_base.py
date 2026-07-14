"""Clean up orphan code after renderBaseRef rewrite."""
c = open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html', encoding='utf-8').read()

# Find the new renderBaseRef closing
marker = "renderMixedContent(tab, 'baseEditorRight');"
idx = c.find(marker)
assert idx > 0, 'Marker not found'

# Find next '};' which is the renderBaseRef closing
close = c.find('\n};', idx)
assert close > idx, 'Closing not found'

# Find 'async function saveBaseTab'
sbt = c.find('async function saveBaseTab', close)
assert sbt > close, 'saveBaseTab not found'

# Delete the orphan code between close+3 and sbt
orphan = c[close+3:sbt]
print(f'Orphan: {len(orphan)} chars, starts with: {orphan[:80]}')

new_c = c[:close+3] + orphan[orphan.find('async function'):] if 'async function' in orphan else c[:close+3] + '\n' + c[sbt:]
# Actually simpler: delete from close+3 to sbt
new_c = c[:close+3] + '\n' + c[sbt:]

open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8').write(new_c)

# Verify
v = open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html', encoding='utf-8').read()
print(f'Before: {len(c)} chars, After: {len(v)} chars, Diff: {len(v)-len(c)}')
print(f'renderBaseRef count: {v.count(\"function renderBaseRef\")}')
print(f'saveBaseTab count: {v.count(\"async function saveBaseTab\")}')
print(f'Orphan cleaned: {orphan[:80]}...' not in v)
