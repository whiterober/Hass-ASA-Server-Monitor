import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py', '/config/preview_server.py')
sftp.close()
# Verify syntax
sin,sout,serr=c.exec_command('python3 -m py_compile /config/preview_server.py 2>&1 && echo "SYNTAX OK"',timeout=10)
print(sout.read().decode())
print(serr.read().decode())
c.close()
