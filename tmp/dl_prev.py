import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
# Download
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py')
# Backup on server
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py', '/tmp/preview_server_backup_20260706.py')
sftp.close()
print('Downloaded OK')
c.close()
