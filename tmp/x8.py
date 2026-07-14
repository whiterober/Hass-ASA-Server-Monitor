import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>&1',timeout=10)
out=sout.read().decode().strip()
err=serr.read().decode().strip()
print('STDOUT:',out[:500] if out else '(empty)')
print('STDERR:',err[:500] if err else '(empty)')
c.close()
