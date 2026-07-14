import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=ssh.exec_command("grep -n 'def make_ic_css' /config/build_lovelace.py",timeout=10)
r=sout.read().decode().strip()
if r: print(r)
# Read the make_ic_css function
sin,sout,serr=ssh.exec_command("sed -n '1400,1600p' /config/build_lovelace.py",timeout=10)
print(sout.read().decode()[:3000])
ssh.close()
