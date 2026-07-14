import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
bl_n=bl.replace('\r\n','\n')
lines=bl_n.split('\n')

for css_name in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS','SHARED_CSS','BASE_RAW_CSS']:
    for i,l in enumerate(lines,1):
        if css_name in l and '=' in l:
            print('{} L{}: {}'.format(css_name,i,l.strip()[:120]))
            # Show a few lines after definition
            for j in range(i,min(len(lines),i+5)):
                if lines[j].strip():
                    print('  L{}: {}'.format(j+1,lines[j][:120]))
            break
ssh.close()
