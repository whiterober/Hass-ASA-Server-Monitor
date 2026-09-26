import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Find all brItemIcon input lines and replace them
# Use the fact that each input has a unique placeholder text

placeholder = 'placeholder=\\"图标URL\\" style=\\"width:110px;padding:2px 6px;font-size:0.65em;margin:0\\"'

count = c.count(placeholder)
print(f'Found {count} brItemIcon inputs')

lines = c.split('\n')
new_lines = []
for line in lines:
    if placeholder in line and 'brItemIcon' in line:
        # Extract the value part
        val_start = line.find('value=\\"') + len('value=\\"')
        val_end = line.find('\\"', val_start)
        val = line[val_start:val_end]

        # Extract the ID parts (si, bi, ri, ci, ii) from the id attribute
        id_start = line.find('id=\\"brItemIcon') + len('id=\\"brItemIcon')
        id_end = line.find('\\"', id_start)
        id_suffix = line[id_start:id_end]  # e.g., '+si+'_'+bi+'_'+ri+'_'+ci+'_'+ii+'

        # Determine if this is render (has esc()) or addStorage (empty)
        is_render = 'esc(item.icon_url' in val
        src_val = val if is_render else '\\"\\"'

        # Build new line
        new_line = line.replace(
            placeholder + '>',
            '\\"><img src=\\"' + src_val + '\\" style=\\"width:22px;height:22px;object-fit:contain;cursor:pointer;flex-shrink:0\\" onclick=\\"event.stopPropagation();openIconPicker(' + id_suffix + ')\\" title=\\"点击换图标\\" onerror=\\"this.style.display=none\\">'
        )
        # Change input to hidden
        new_line = new_line.replace('<input id=\\"brItemIcon', '<input type=\\"hidden\\" id=\\"brItemIcon')
        new_lines.append(new_line)
        print(f'Fixed: val={val[:30]}')
    else:
        new_lines.append(line)

c = '\n'.join(new_lines)

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
