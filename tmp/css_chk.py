import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sin,sout,serr=ssh.exec_command('grep -c "make_ic_css\|IC_CSS\|card_mod" /config/build_lovelace.py /config/preview_server.py',timeout=10)
print(sout.read().decode())
ssh.close()
