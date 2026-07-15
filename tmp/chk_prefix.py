import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Check icon group auto-color CSS
sin,sout,serr=ssh.exec_command("grep -n -A1 'ig-img.ic-auto' /config/build_lovelace.py",timeout=10)
print("=== icon group (ig-img) ===")
print(sout.read().decode())
# Check info_card image auto-color CSS
sin,sout,serr=ssh.exec_command("grep -n -A1 'info-card-block img.ic-auto' /config/build_lovelace.py",timeout=10)
print("=== info_card (img) ===")
print(sout.read().decode())
ssh.close()
