import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Check if ic-block affects icon groups
sin,sout,serr=ssh.exec_command("grep -n 'ig.*ic-block\\|ic-block.*ig' /config/build_lovelace.py",timeout=10)
print("=== ig + ic-block ===")
print(sout.read().decode())
# Also check DOM rendering for icon group + block mode
sin,sout,serr=ssh.exec_command("sed -n '1895,1930p' /config/build_lovelace.py",timeout=10)
print("\n=== DOM L1895-1930 ===")
print(sout.read().decode())
ssh.close()
