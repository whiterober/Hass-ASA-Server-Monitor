import paramiko,os,shutil
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
local=r'b:\项目\Hass ASA Server Monitor'
for remote,fname in [('/config/build_lovelace.py','build_lovelace.py'),('/config/preview_server.py','preview_server.py')]:
    with sftp.open(remote,'r') as f:data=f.read().decode()
    lp=os.path.join(local,fname)
    if os.path.exists(lp): shutil.copy2(lp,lp+'.bak3')
    with open(lp,'w',encoding='utf-8',newline='') as f:f.write(data)
    print('{} : {} chars'.format(fname,len(data)))
sftp.close()
ssh.close()
print('Sync done')
