import paramiko,os,shutil
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
bak_dir=r'c:\Users\white\.copilot\bak\asa_v1338_20260714'
os.makedirs(bak_dir,exist_ok=True)
sftp=ssh.open_sftp()
for remote,local in [('/config/lovelace','lovelace'),('/config/lovelace.lovelace','lovelace.lovelace'),
    ('/config/build_lovelace.py','build_lovelace.py'),('/config/preview_server.py','preview_server.py'),
    ('/config/www/asa-data/server_rules.json','server_rules.json'),
    ('/config/www/asa-data/tribe_ops.json','tribe_ops.json'),
    ('/config/www/asa-data/asa_base_quick_ref.json','asa_base_quick_ref.json')]:
    try:
        with sftp.open(remote,'r') as f:data=f.read()
        with open(os.path.join(bak_dir,local),'wb') as f:f.write(data)
        print('OK: {} ({} bytes)'.format(local,len(data)))
    except Exception as e:print('FAIL: {} {}'.format(local,e))
sftp.close()
src=r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html'
shutil.copy2(src,os.path.join(bak_dir,'asa-admin.html'))
print('OK: asa-admin.html ({} bytes)'.format(os.path.getsize(src)))
print('Backup: {} files in {}'.format(len(os.listdir(bak_dir)),bak_dir))
ssh.close()
