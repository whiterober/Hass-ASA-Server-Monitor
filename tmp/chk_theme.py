import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Search for theme detection injection
sin,sout,serr=ssh.exec_command("grep -n 'MutationObserver\\|data-theme\\|getComputedStyle\\|onerror.*var d=this' /config/build_lovelace.py | head -15",timeout=10)
print(sout.read().decode()[:2000])
ssh.close()
