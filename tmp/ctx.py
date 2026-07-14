import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
content=content.replace('\r\n','\n')
lines=content.split('\n')

# Show all remaining dead refs with context
for target_ln in [1551,1584,2161,2169,2524,2590,2638,2649,2708,2724,2796,2872,3138]:
    # show 3 lines before and 5 after
    print(f'\n=== L{target_ln} ===')
    s=max(0,target_ln-4)
    e=min(len(lines),target_ln+6)
    for i in range(s,e):
        marker='>>>' if i+1==target_ln else '   '
        print(f'{marker} L{i+1}: {lines[i]}')
c.close()
