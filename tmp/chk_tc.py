import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Check if text_color exists in SERVER_MAP
sin,sout,serr=ssh.exec_command("grep -n 'text_color' /config/build_lovelace.py",timeout=10)
print("=== text_color ===")
print(sout.read().decode())
# Check what color is actually used for block mode text
sin,sout,serr=ssh.exec_command("grep -A1 'ic-block.*color' /config/build_lovelace.py | head -20",timeout=10)
print("\n=== block text color ===")
print(sout.read().decode())
ssh.close()
