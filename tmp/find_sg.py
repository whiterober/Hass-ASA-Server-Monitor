import paramiko
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command("grep -n 'server_grid' /config/build_lovelace.py",timeout=10)
lines=sout.read().decode().strip().split('\n')
for l in lines:
    if l.strip():
        parts=l.split(':',1)
        print(f'L{parts[0]}: {parts[1][:120]}')
c.close()
