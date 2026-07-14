import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    lines=content.split('\n')
    for i,l in enumerate(lines,1):
        if kw in l:
            print(f'L{i}: {l.strip()[:120]}')
c.close()
