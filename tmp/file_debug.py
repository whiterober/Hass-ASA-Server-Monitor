import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_f2.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_f2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace debug with file write
old = "if icon_url: sys.stderr.write('ICON: '+icon_url[:60]+chr(10))"
new = "open('/tmp/ps_debug.log','a').write('ICON:'+icon_url+'\\n')"
content = content.replace(old, new)

# Also add entry point debug
old2 = "elif bt == 'base_storage' and b.get('rows'):"
new2 = "elif bt == 'base_storage' and b.get('rows'):\n                        open('/tmp/ps_debug.log','a').write('ENTER base_storage rows='+str(len(b[\"rows\"]))+'\\n')"
content = content.replace(old2, new2)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_f2.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_f2.py', '/config/preview_server.py')
sftp.close()

# Clear old log
sin,sout,serr=c.exec_command('rm -f /tmp/ps_debug.log',timeout=5)

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())

# Read debug log
sin,sout,serr=c.exec_command('cat /tmp/ps_debug.log 2>/dev/null || echo "(no log)"',timeout=10)
print("LOG:", sout.read().decode())

c.close()
