import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Search for all ic-linear and ic-block CSS rules
sin,sout,serr=ssh.exec_command("grep -n 'ic-linear\\|ic-block' /config/build_lovelace.py",timeout=10)
lines=sout.read().decode().strip().split('\n')
for l in lines:
    if l.strip():
        print(l[:200])
ssh.close()
