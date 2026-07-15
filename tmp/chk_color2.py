import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=ssh.exec_command("grep -n 'ic-auto-dark\\|ic-auto-light\\|invert\\|color-mix' /config/build_lovelace.py",timeout=10)
lines=sout.read().decode().strip().split('\n')
for l in lines:
    if l.strip():
        print(l[:150])
ssh.close()
