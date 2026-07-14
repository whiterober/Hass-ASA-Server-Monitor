import paramiko
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>&1 | tail -20',timeout=15)
out=sout.read().decode().strip()
err=serr.read().decode().strip()
print(out[-500:] if len(out)>500 else out)
if err: print('STDERR:',err[-300:])
c.close()
