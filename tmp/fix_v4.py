import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_v4.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v4.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: remove the broken category lines, restore original row line, keep body condition
# Find and fix lines 210-222 area
lines = content.split('\n')
new_lines = []
skip_until_normal = False
for i, line in enumerate(lines):
    if 'Render categories for storage columns' in line:
        skip_until_normal = True
        continue
    if skip_until_normal:
        if 'rows_html.append' in line and "colspan" in line and "col2" in line:
            # Replace with simple version (empty col2 for now - body will handle storage)
            indent = line[:len(line) - len(line.lstrip())]
            replacement = indent + "rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\"></td></tr>')"
            new_lines.append(replacement)
            skip_until_normal = False
            continue
        else:
            # Skip all category-related lines
            continue
    new_lines.append(line)

content = '\n'.join(new_lines)

# Now revert to use body for ALL blocks
content = content.replace("if bt != 'base_storage' and b.get('body'):", "if b.get('body'):")

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v4.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v4.py', '/config/preview_server.py')
sftp.close()

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())
print("ERR:", serr.read().decode()[:200])

c.close()
