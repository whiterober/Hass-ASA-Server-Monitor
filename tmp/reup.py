import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py','/config/preview_server.py')
sftp.close()
sin,sout,serr=c.exec_command('grep -c "_render_item" /config/preview_server.py 2>&1',timeout=10)
print('grep:',sout.read().decode().strip(),serr.read().decode().strip())
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py Isl base_quick_ref 2>&1 | tail -1',timeout=30)
print('gen:',sout.read().decode().strip())
c.close()
