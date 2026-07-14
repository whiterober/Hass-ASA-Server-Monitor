import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check render_asa.py content
sin,sout,serr=c.exec_command('cat /config/render_asa.py',timeout=10)
print('=== render_asa.py ===')
print(sout.read().decode()[:3000])

c.close()
