import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
lines=content.split('\n')
new_lines=lines[:2707]+lines[2729:]
new_content='\n'.join(new_lines)
sftp=c.open_sftp()
with sftp.open('/tmp/_orphan_fix.py','w') as f:f.write(new_content)
sftp.close()
sin,sout,serr=c.exec_command('python3 -m py_compile /tmp/_orphan_fix.py 2>&1 && echo OK || echo FAIL',timeout=10)
r=sout.read().decode().strip()
print('Syntax:',r)
if 'OK' in r:
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(new_content)
    sftp.close()
    print(f'OK: {len(lines)}->{len(new_lines)} lines')
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>&1 | head -3',timeout=10)
    out=sout.read().decode().strip()
    print('Preview:', 'OK' if '<!DOCTYPE' in out else 'FAIL: '+out[:150])
    if '<!DOCTYPE' in out:
        sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref > /config/www/preview_tab.html 2>&1 && echo DONE || echo FAIL',timeout=10)
        print(sout.read().decode().strip())
c.close()
