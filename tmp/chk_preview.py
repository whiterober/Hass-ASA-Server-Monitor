import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check if preview_tab.html is static file
sin,sout,serr=c.exec_command('ls -la /config/www/preview_tab.html; echo "==="; head -5 /config/www/preview_tab.html',timeout=10)
print(sout.read().decode())

# Check if preview_server.py can be run
sin,sout,serr=c.exec_command('head -3 /config/preview_server.py',timeout=10)
print(sout.read().decode())

c.close()
