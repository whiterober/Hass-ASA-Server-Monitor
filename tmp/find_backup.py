import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check for backup
sin,sout,serr=c.exec_command("ls -t /config/www/asa-data/asa_base_quick_ref* 2>/dev/null | head -5; echo '---'; ls -t /config/www/asa-data/*.bak 2>/dev/null | head -5; echo '---'; ls -t /config/backup/*base* 2>/dev/null | head -5",timeout=10)
print(sout.read().decode())

c.close()
