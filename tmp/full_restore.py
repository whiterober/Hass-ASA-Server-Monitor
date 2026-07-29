import paramiko, os, shutil

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
bak = r'B:\项目\Hass ASA Server Monitor\bak\baseline_20260729_155105'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h, port=p, username=u, password=pw, look_for_keys=False, allow_agent=False)
sftp = c.open_sftp()

# 1-8: Server files
server_files = [
    ('asa-admin-v1653.html', '/config/www/asa-data/'),
    ('build_lovelace.py', '/config/'),
    ('preview_server.py', '/config/'),
    ('server_colors.json', '/config/'),
    ('icon_anti_color.json', '/config/www/asa-data/'),
    ('server_rules.json', '/config/www/asa-data/'),
    ('tribe_ops.json', '/config/www/asa-data/'),
    ('asa_base_quick_ref.json', '/config/www/asa-data/'),
]

for fname, remote_dir in server_files:
    src = os.path.join(bak, fname)
    remote = remote_dir + fname
    sftp.put(src, remote)
    print(f'  ✅ {fname}')

sftp.close()
c.close()

# 9-10: Local files
local_files = [
    ('lovelace', r'A:\NetSarang\Xftp 8\Temporary\lovelace'),
    ('lovelace.lovelace', r'A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace'),
]
for fname, dst in local_files:
    src = os.path.join(bak, fname)
    shutil.copy2(src, dst)
    print(f'  ✅ {fname}')

print('\n10/10 restored')
