import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\find_backup2.py','/tmp/_fb2.py')
sftp.close()
sin,sout,serr=c.exec_command('python3 /tmp/_fb2.py',timeout=15)
print(sout.read().decode())
c.close()
