import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=ssh.exec_command('wc -l /config/build_lovelace.py; echo ---; tail -20 /config/build_lovelace.py',timeout=10)
print(sout.read().decode())

# Check what was at the end of v1337c
import os
v1337c=r'c:\Users\white\.copilot\bak\asa_v1337c_20260714\build_lovelace.py'
sz=os.path.getsize(v1337c)
print('v1337c size:',sz)

# Compare with current
sin,sout,serr=ssh.exec_command('wc -c /config/build_lovelace.py',timeout=10)
print('Current:',sout.read().decode().strip())

ssh.close()
