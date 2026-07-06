import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py','/config/preview_server.py')
sftp.close()
# Compile
sin,sout,serr=c.exec_command('python3 -m py_compile /config/preview_server.py 2>&1 && echo OK',timeout=10)
r1=sout.read().decode().strip()
print('Compile:',r1)
# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py Isl base_quick_ref 2>&1 | tail -1',timeout=30)
r2=sout.read().decode().strip()
print('Generate:',r2)
# Check CSS presence + img classes
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:
    html=f.read().decode()
print('ic-auto-dark in HTML:', 'ic-auto-dark' in html)
print('base-table invert CSS:', '#base-table img.ic-auto-dark' in html)
# Count auto-class images
auto_imgs=len(re.findall(r'class="ic-auto-',html))
print(f'Images with ic-auto-* class: {auto_imgs}')
sftp.close()
c.close()
