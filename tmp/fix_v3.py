import paramiko, re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_v3.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v3.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Revert condition back to original (use body for all)
old_cond = "if bt != 'base_storage' and b.get('body'):"
new_cond = "if b.get('body'):"
content = content.replace(old_cond, new_cond)

# Add image injection into body HTML for base_storage blocks
# After b['body'] is appended, inject images from rows[i].images[0].image_url
old_body_append = "body_parts.append(b['body'])"
new_body_append = """body_parts.append(b['body'])
                    elif bt == 'base_storage' and b.get('rows'):
                        # Inject images into body HTML (replaces empty device-icon-wrapper)
                        body_html = ''
                        rows = b['rows']
                        for ri, row in enumerate(rows):
                            img_url = (row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')
                            if img_url and body_html:
                                # Find the ri-th device-icon-wrapper and inject img
                                import re as _re
                                wrappers = list(_re.finditer(r'<div class=\"device-icon-wrapper[^\"]*\"></div>', body_html))
                                if ri < len(wrappers):
                                    w = wrappers[ri]
                                    img_tag = '<img src=\"'+img_url+'\" style=\"width:30px;height:30px;object-fit:contain\" />'
                                    body_html = body_html[:w.start()] + w.group().replace('></div>','>'+img_tag+'</div>') + body_html[w.end():]
                        if body_html:
                            body_parts.append(body_html)
                    elif bt == 'base_storage' and b.get('rows'):"""

# Wait, this is getting too complex. Let me use a simpler approach.
# Just fix the structured rendering to include storage data properly.
# Revert the complex replacement above.

# Clean approach: just make the structured base_storage rendering complete
# by adding category rendering to the storage column.

# First find the exact row line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'rows_html.append' in line and "colspan" in line:
        # This is the row rendering line
        indent = line[:len(line) - len(line.lstrip())]
        
        # Replace with version that includes storage data
        new_lines = [
            indent + "                        # Render categories for storage columns",
            indent + "                        cat_items = []",
            indent + "                        for c in row.get('categories', []):",
            indent + "                            items_html = '<br>'.join([(i.get('name','') or '') for i in c.get('items', [])])",
            indent + "                            if items_html:",
            indent + "                                label = c.get('label','')",
            indent + "                                cat_items.append(('<span class=\"text-bold\">'+label+'</span><br>'+items_html) if label else items_html)",
            indent + "                        col2 = '<br>'.join(cat_items) if cat_items else ''",
            indent + "                        rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\">'+col2+'</td></tr>')",
        ]
        # Remove the old line
        lines[i] = '\n'.join(new_lines)
        print(f"Fixed line {i+1}")
        break

content = '\n'.join(lines)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v3.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v3.py', '/config/preview_server.py')
sftp.close()

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())
print("ERR:", serr.read().decode()[:300])

# Check
sin,sout,serr=c.exec_command('grep -c "Cryofridge\|Cloth_Boots\|text-bold" /config/www/preview_tab.html',timeout=10)
print("Matches:", sout.read().decode())

c.close()
