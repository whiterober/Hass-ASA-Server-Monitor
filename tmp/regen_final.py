import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Regenerate for Isl:0
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print(sout.read().decode())

# Verify img count  
sin,sout,serr=c.exec_command('grep -c "<img src=" /config/www/preview_tab.html',timeout=10)
print("img tags in HTML:", sout.read().decode())

c.close()
