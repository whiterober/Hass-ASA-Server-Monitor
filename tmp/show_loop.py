import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:
    lines=f.read().decode().split('\n')
# Show lines 170-220 to see the full loop structure
for i in range(169,220):
    print(f'{i+1}: {lines[i]}')
sftp.close()
c.close()
