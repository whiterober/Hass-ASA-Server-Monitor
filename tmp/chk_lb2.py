import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
# Get all CSS rules involving ic-linear or ic-block with full context
sin,sout,serr=ssh.exec_command("sed -n '69,130p' /config/build_lovelace.py",timeout=10)
l1=sout.read().decode()
# Also get icon group rules
sin,sout,serr=ssh.exec_command("sed -n '2520,2550p' /config/build_lovelace.py",timeout=10)
l2=sout.read().decode()
# Also get DOM rendering rules
sin,sout,serr=ssh.exec_command("sed -n '1820,2000p' /config/build_lovelace.py",timeout=10)
l3=sout.read().decode()
print("=== CSS rules (L69-130) ===")
print(l1)
print("\n=== Icon group CSS (L2520-2550) ===")
print(l2)
print("\n=== DOM rendering (L1820-2000, partial) ===")
print(l3[:3000])
ssh.close()
