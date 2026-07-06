import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_final.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug using sys.stderr (sys is already imported at top)
old = "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''\n                            icon = '<img"
new = "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''\n                            if icon_url: sys.stderr.write('ICON: '+icon_url[:60]+chr(10))\n                            icon = '<img"
content = content.replace(old, new)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_final.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_final.py', '/config/preview_server.py')
sftp.close()

sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("OUT:", sout.read().decode())
err_out = serr.read().decode()
print("ERR:", err_out[:500] if err_out else "(empty)")

c.close()
