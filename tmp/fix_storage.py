import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Strategy: keep body rendering for all blocks (revert condition),
# but clear the body field in the JSON for base_storage blocks so
# they get re-generated with current images on next preview_server.py run.
# Then regenerate preview_server.py to remove the body field check.
# This way the Python renders ALL content from structured data.

# Step 1: Revert preview_server.py condition
sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_revert.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_revert.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Revert to original: use body for all, fall through to structured
old = "if bt != 'base_storage' and b.get('body'):"
new = "if b.get('body'):"
content = content.replace(old, new)

# Also add structured rendering for storage column content  
# Find the base_storage rendering and add material/creature columns
old_row = "rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\"></td></tr>')"

# Generate storage column content from categories
new_row = """                        # Render categories for storage columns
                        cat_parts = []
                        for c in row.get('categories', []):
                            items_html = '<br>'.join([(i.get('name','') or '') for i in c.get('items', [])])
                            if items_html:
                                label = c.get('label','')
                                cat_parts.append(('<span class="text-bold">'+label+'</span><br>'+items_html) if label else items_html)
                        col2 = '<br>'.join(cat_parts) if cat_parts else ''
                        rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\">'+col2+'</td></tr>')"""

content = content.replace(old_row, new_row)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_revert.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Step 2: Clear body field in JSON for base_storage blocks, so body takes precedence
# Actually, wait - the issue is the opposite. body has old HTML without new images.
# I should KEEP the bt != 'base_storage' condition AND add storage rendering.
# Let me redo this properly.

# Revert back to bt != base_storage
content = content.replace("if b.get('body'):", "if bt != 'base_storage' and b.get('body'):")

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_revert.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_revert.py', '/config/preview_server.py')
sftp.close()

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())
print("ERR:", serr.read().decode()[:200])

# Check
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html; echo "---"; grep -c "<img src=" /config/www/preview_tab.html',timeout=10)
print("Verify:", sout.read().decode())

c.close()
