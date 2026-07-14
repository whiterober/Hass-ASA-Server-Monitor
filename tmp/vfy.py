import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('python3 -m py_compile /config/build_lovelace.py 2>&1 && echo OK || echo FAIL',timeout=10)
r=sout.read().decode().strip()
print('Syntax:', 'OK' if 'OK' in r else r[:200])
sin,sout,serr=c.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>/dev/null',timeout=10)
out=sout.read().decode().strip()
print('Preview:', out[:80])
sin,sout,serr=c.exec_command('wc -l /config/build_lovelace.py',timeout=10)
print('Lines:', sout.read().decode().strip())
# Count remaining dead references
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    n=bl.count(kw)
    if n>0: print(f'{kw}: {n} refs left')
c.close()
