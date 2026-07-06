import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check preview_server.py condition
sin,sout,serr=c.exec_command('grep -n "b.get.*body\|bt.*base_storage" /config/preview_server.py',timeout=10)
print("Conditions:", sout.read().decode())

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py Isl:0 base_quick_ref 2>&1',timeout=30)
print("Regen:", sout.read().decode())

# Verify  
sin,sout,serr=c.exec_command('grep -c text-bold /config/www/preview_tab.html; grep -c "img src=" /config/www/preview_tab.html; wc -c /config/www/preview_tab.html',timeout=10)
print("Verify:", sout.read().decode())

c.close()
