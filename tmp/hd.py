import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Get head of preview
si,so,se = c.exec_command('head -80 /config/www/preview_tab.html',timeout=5)
print(so.read().decode())

# Get tail
si,so,se = c.exec_command('tail -30 /config/www/preview_tab.html',timeout=5)
print('---TAIL---')
print(so.read().decode())

c.close()
