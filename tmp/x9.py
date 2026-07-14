import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('sed -n 2700,2740p /config/build_lovelace.py',timeout=10)
lines=sout.read().decode().split('\n')
for i,l in enumerate(lines):
    print(f'{2700+i}: {l}')
c.close()
