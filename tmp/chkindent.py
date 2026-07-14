import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:lines=f.read().decode().split('\n')
sftp.close()

# Check lines around server_grid references
for ln in [3276,3277,3278,3148,3089,3081]:
    if ln<=len(lines):
        l=lines[ln-1]
        # Show first 8 chars as repr
        prefix=repr(l[:16])
        print(f'L{ln}: prefix={prefix} rest={l[16:60] if len(l)>16 else ""}')
c.close()
