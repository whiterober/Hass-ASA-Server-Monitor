import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
cmd = 'grep -n "device_icon_url" /config/build_lovelace.py | head -10; echo ---; grep -n "images\[0\]" /config/build_lovelace.py | head -10'
sin,sout,serr=c.exec_command(cmd,timeout=10)
print(sout.read().decode())
c.close()
