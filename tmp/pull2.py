import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

local = r'b:\项目\Hass ASA Server Monitor\tmp\preview_server.py'
sftp = c.open_sftp()
sftp.get('/config/preview_server.py', local)
sftp.close()
c.close()
print("Pulled preview_server.py")
