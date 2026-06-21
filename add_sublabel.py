with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# The brCatLabel line in the file looks like:
# html += '<input id=\"brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"'+esc(cat.label||'')+'\" placeholder=\"分类名\" style=\"width:90px;padding:4px 8px;font-size:0.75em;font-weight:bold;margin:0\">';
# After this line, I need to add:
# html += '<input id=\"brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\" value=\"'+esc(cat.sub_label||'')+'\" placeholder=\"副标签\" style=\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\">';

# Find the exact pattern to replace
old1 = "html += '<input id=\\\"brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" value=\\\"'+esc(cat.label||'')+'\\\" placeholder=\\\"分类名\\\" style=\\\"width:90px;padding:4px 8px;font-size:0.75em;font-weight:bold;margin:0\\\">';"

new1 = old1 + "\n                html += '<input id=\\\"brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" value=\\\"'+esc(cat.sub_label||'')+'\\\" placeholder=\\\"副标签\\\" style=\\\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\\\">';"

c = c.replace(old1, new1)
print('Render fix:', c.count('brCatSubLabel'))

# Also fix addStorageCat
old2 = "h += '<input id=\\\"brCatLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" value=\\\"\\\" placeholder=\\\"分类名\\\" style=\\\"width:90px;padding:4px 8px;font-size:0.75em;font-weight:bold;margin:0\\\">';"

new2 = old2 + "\n  h += '<input id=\\\"brCatSubLabel'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" value=\\\"\\\" placeholder=\\\"副标签\\\" style=\\\"width:60px;padding:4px 8px;font-size:0.7em;margin:0\\\">';"

c = c.replace(old2, new2)
print('AddStorageCat fix:', c.count('brCatSubLabel'))

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
