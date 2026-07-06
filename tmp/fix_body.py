import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix3.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix3.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: base_storage should NOT use cached body
old_cond = "if b.get('body'):\n                        body_parts.append(b['body'])\n                    elif bt == 'base_storage' and b.get('rows'):"
new_cond = "if bt != 'base_storage' and b.get('body'):\n                        body_parts.append(b['body'])\n                    elif bt == 'base_storage' and b.get('rows'):"

content = content.replace(old_cond, new_cond)
print("Replaced:", old_cond in content)  # should be False after replacement

# Remove debug lines
content = content.replace("open('/tmp/ps_debug.log','a').write('ENTER base_storage rows='+str(len(b[\"rows\"]))+'\\n')\n                        ", "")
content = content.replace("\n                            open('/tmp/ps_debug.log','a').write('ICON:'+icon_url+'\\n')", "")

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix3.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix3.py', '/config/preview_server.py')
sftp.close()

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())

# Verify
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html; echo "---"; grep -c "<img src=" /config/www/preview_tab.html',timeout=10)
print("Verify:", sout.read().decode())

c.close()
