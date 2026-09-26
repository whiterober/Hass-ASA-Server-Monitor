with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the +物品 button in the render template
target = 'addStorageItem('
lines = c.split('\n')
for i, line in enumerate(lines):
    if 'addStorageItem(' in line and '+ 物品' in line and 'cat.items' in line:
        print(f'Found button at line {i+1}')
        # Remove this line
        lines[i] = ''
        # Now find where to insert after items
        for j in range(i+1, min(i+50, len(lines))):
            if "html += '</div>'; // sr-items" in lines[j] or ("html += '</div>'" in lines[j] and j > i+5):
                # Insert before the closing div
                btn = "                html += '<button class=\"btn-small btn-primary\" onclick=\"addStorageItem('+si+','+bi+','+ri+','+ci+')\" style=\"padding:1px 6px;font-size:0.6em;margin-top:4px\">+ 物品</button>';"
                lines.insert(j, btn)
                print(f'Inserted button before line {j+1}')
                break
        else:
            print('Could not find insertion point')
        break
else:
    print('Button not found')

c = '\n'.join(lines)
with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
