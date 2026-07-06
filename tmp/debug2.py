import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps2.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the icon_url line with debug
old = "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''\n                            if icon_url: print('DEBUG ICON:', icon_url[:60], file=__import__('sys').stderr)"
new = "images_raw = row.get('images'); print('DEBUG images:', repr(images_raw)[:100] if images_raw else 'NONE', file=__import__('sys').stderr); icon_url = (images_raw[0].get('image_url','') if images_raw and len(images_raw)>0 else '')"
content = content.replace(old, new)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps2.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps2.py', '/config/preview_server.py')
sftp.close()

sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("STDERR:", serr.read().decode()[:500])
print("STDOUT:", sout.read().decode())

c.close()
