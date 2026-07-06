import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('grep -c device_icon /config/preview_server.py; grep -c "image_url" /config/preview_server.py | head -1; md5sum /config/preview_server.py',timeout=10)
print(sout.read().decode())
c.close()
