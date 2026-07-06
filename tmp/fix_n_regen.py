import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Fix the debug line (__import__('sys') might not work in preview_server context)
# Replace with proper sys.stderr
sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove debug line, restore original working code
content = content.replace(
    "images_raw = row.get('images'); print('DEBUG images:', repr(images_raw)[:100] if images_raw else 'NONE', file=__import__('sys').stderr); icon_url = (images_raw[0].get('image_url','') if images_raw and len(images_raw)>0 else '')",
    "icon_url = row.get('images',[{}])[0].get('image_url','') if row.get('images') else ''"
)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix.py', '/config/preview_server.py')
sftp.close()

# Regenerate  
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print(sout.read().decode())

# Check
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html; echo "---"; grep -c "<img src=" /config/www/preview_tab.html',timeout=10)
print(sout.read().decode())

c.close()
