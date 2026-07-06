import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
# Check shell_command
sin,sout,serr=c.exec_command('grep -A3 "preview_tab\|preview_server" /config/configuration.yaml | head -20',timeout=10)
print(sout.read().decode())
c.close()
