import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Pull, add debug, upload, regenerate
sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_debug.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_debug.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug after icon_url calculation
old = "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''\n                            icon = '<img"
new = "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''\n                            if icon_url: print('DEBUG ICON:', icon_url[:60], file=__import__('sys').stderr)\n                            icon = '<img"
content = content.replace(old, new)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_debug.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Upload and run
sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_debug.py', '/config/preview_server.py')
sftp.close()

sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("STDERR:", serr.read().decode())
print("STDOUT:", sout.read().decode())

# Verify
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html',timeout=10)
print("Cloth_Boots in HTML:", sout.read().decode())

c.close()
