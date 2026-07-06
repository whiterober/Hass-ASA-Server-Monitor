import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py base_quick_ref base_quick_ref 2>&1 | tail -5',timeout=30)
print("STDOUT:",sout.read().decode())
print("STDERR:",serr.read().decode())
c.close()
