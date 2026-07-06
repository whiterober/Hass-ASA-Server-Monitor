import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Simple grep for Cloth_Boots
sin,sout,serr=c.exec_command("grep 'Cloth_Boots' /config/www/asa-data/asa_base_quick_ref.json",timeout=10)
out = sout.read().decode()
print("JSON:", out[:200] if out else "NOT FOUND")

# Check preview HTML
sin,sout,serr=c.exec_command("grep 'Cloth_Boots' /config/www/preview_tab.html",timeout=10)
out2 = sout.read().decode()
print("HTML:", out2[:200] if out2 else "NOT FOUND")

c.close()
