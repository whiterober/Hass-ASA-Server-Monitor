import paramiko, os, shutil, time
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

bak_dir = r'c:\Users\white\.copilot\bak\asa_v1337_20260714'
os.makedirs(bak_dir, exist_ok=True)

files = {
    # remote path -> local filename
    '/config/build_lovelace.py': 'build_lovelace.py',
    '/config/preview_server.py': 'preview_server.py',
    '/config/lovelace': 'lovelace',
    '/config/lovelace.lovelace': 'lovelace.lovelace',
    '/config/www/asa-data/server_rules.json': 'server_rules.json',
    '/config/www/asa-data/tribe_ops.json': 'tribe_ops.json',
    '/config/www/asa-data/asa_base_quick_ref.json': 'asa_base_quick_ref.json',
}

sftp=c.open_sftp()
for remote, local in files.items():
    try:
        with sftp.open(remote,'r') as f: data=f.read()
        local_path = os.path.join(bak_dir, local)
        with open(local_path, 'wb') as f: f.write(data)
        print(f'OK: {local} ({len(data)} bytes)')
    except Exception as e:
        print(f'FAIL: {local}: {e}')
sftp.close()

# Copy local asa-admin.html
local_html = r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html'
shutil.copy2(local_html, os.path.join(bak_dir, 'asa-admin.html'))
print(f'OK: asa-admin.html ({os.path.getsize(local_html)} bytes)')

# Also copy server v1337
try:
    sftp=c.open_sftp()
    with sftp.open('/config/www/asa-data/asa-admin-v1337.html','r') as f: data=f.read()
    with open(os.path.join(bak_dir, 'asa-admin-v1337.html'), 'wb') as f: f.write(data)
    print(f'OK: asa-admin-v1337.html ({len(data)} bytes)')
    sftp.close()
except Exception as e:
    print(f'FAIL: asa-admin-v1337.html: {e}')

print(f'\nBackup complete: {bak_dir}')
print(f'Files: {len(os.listdir(bak_dir))}')
c.close()
