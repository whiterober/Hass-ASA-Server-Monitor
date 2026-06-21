with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix: openIconPicker('+si+'_'+bi+'_'+ri+'_'+ci+'_'+ii+') → commas
old = "openIconPicker('+si+'_'+bi+'_'+ri+'_'+ci+'_'+ii+')"
new = "openIconPicker('+si+','+bi+','+ri+','+ci+','+ii+')"
count = c.count(old)
print(f'Found: {count}')
c = c.replace(old, new)

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
