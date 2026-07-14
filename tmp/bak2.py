import paramiko,os,shutil
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
bak=r'c:\Users\white\.copilot\bak\asa_v1337b_20260714'
os.makedirs(bak,exist_ok=True)
sftp=c.open_sftp()
files=[
    ('/config/build_lovelace.py','build_lovelace.py'),
    ('/config/preview_server.py','preview_server.py'),
    ('/config/lovelace','lovelace'),
    ('/config/lovelace.lovelace','lovelace.lovelace'),
    ('/config/www/asa-data/server_rules.json','server_rules.json'),
    ('/config/www/asa-data/tribe_ops.json','tribe_ops.json'),
    ('/config/www/asa-data/asa_base_quick_ref.json','asa_base_quick_ref.json'),
]
for remote,local in files:
    try:
        with sftp.open(remote,'r') as f:
            data=f.read()
        with open(os.path.join(bak,local),'wb') as f:
            f.write(data)
        print('OK: {} ({} bytes)'.format(local,len(data)))
    except Exception as e:
        print('FAIL: {} {}'.format(local,e))
sftp.close()
# Copy local asa-admin.html
local_html=r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html'
shutil.copy2(local_html,os.path.join(bak,'asa-admin.html'))
print('OK: asa-admin.html ({} bytes)'.format(os.path.getsize(local_html)))
print('Done: {} files in {}'.format(len(os.listdir(bak)),bak))
c.close()
