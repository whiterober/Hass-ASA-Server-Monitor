import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_v5.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v5.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 210-211 area (0-indexed: 209-210)
for i in range(208, 215):
    print(f"L{i+1}: {repr(lines[i][:80])}")

# Fix indentation: line 210 should have same indent as line 208
# Line 208 starts with "                        for row"
# Line 210 should start with same indent
target_indent = "                        "
for i in range(208, min(215, len(lines))):
    stripped = lines[i].lstrip()
    if stripped and not stripped.startswith('#'):
        lines[i] = target_indent + stripped

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v5.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Also ensure condition is correct
content = ''.join(lines)
if "if bt != 'base_storage'" in content:
    content = content.replace("if bt != 'base_storage' and b.get('body'):", "if b.get('body'):")

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v5.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_v5.py', '/config/preview_server.py')
sftp.close()

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())
print("ERR:", serr.read().decode()[:200])

c.close()
