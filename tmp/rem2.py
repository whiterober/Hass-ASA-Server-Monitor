import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
content=content.replace('\r\n','\n')
lines=content.split('\n')

# Show remaining refs
for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    for i,l in enumerate(lines,1):
        if kw in l:
            # Show the line and a few after for context
            print('=== {} L{} ==='.format(kw,i))
            for j in range(i-1,min(len(lines),i+5)):
                print('L{}: {}'.format(j+1,lines[j][:120]))
            break
c.close()
