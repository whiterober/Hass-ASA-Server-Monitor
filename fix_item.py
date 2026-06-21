import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace all input#brItemIcon with hidden+img in both render and addStorage templates
# Use regex to match the input tag and capture the value part

# Pattern for renderBaseRef: has esc(item.icon_url||'')
pattern1 = r"<input id=\\\"brItemIcon(\+\w+\+'_'\+)+\\\" value=\\\"\+esc\(item\.icon_url\|\|''\)\+'\\\" placeholder=\\\"图标URL\\\" style=\\\"width:110px;padding:2px 6px;font-size:0\.65em;margin:0\\\">"
repl1 = r'<input type="hidden" id="brItemIcon\1" value="\'+esc(item.icon_url||\'\')+\'"><img src="\'+esc(item.icon_url||\'\')+\'" style="width:22px;height:22px;object-fit:contain;cursor:pointer;flex-shrink:0" onclick="event.stopPropagation();openIconPicker(\1)" title="点击换图标" onerror="this.style.display=none">'
# The \1 backreference captures the ID suffix like '+si+'_'+bi+'_'+ri+'_'+ci+'_'+ii+'

# This regex is too complex. Let me just do simple string replacement on the placeholder part
old_placeholder = 'placeholder=\\"图标URL\\" style=\\"width:110px;padding:2px 6px;font-size:0.65em;margin:0\\">'
count = c.count(old_placeholder)
print(f'Found {count} icon URL inputs')

# Replace the input start 'id=' with 'type="hidden" id='
c = c.replace('<input id=\\"brItemIcon', '<input type=\\"hidden\\" id=\\"brItemIcon')

# Replace closing of input tag + add img
# The pattern after the value is: '\\">' followed by the next element
# Actually the placeholder+style ends with '\\">'
# Replace: '\\">' → the end of input + start of img
c = c.replace(old_placeholder, '\\"><img src=\\"')

# Now we need to add the rest of the img tag after each brItemIcon hidden input
# But each one has a different img src. The render one uses esc(item.icon_url), addStorage uses empty.
# Let me handle this differently:
# For lines with 'esc(item.icon_url' before brItemIcon, use the esc version
# For lines without, use empty src

# Actually, let me just do two passes

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Step 1 done - replaced inputs with hidden+img start')
