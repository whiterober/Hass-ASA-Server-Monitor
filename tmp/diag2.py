import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Check lovelace content for current vs old indicators
sftp=ssh.open_sftp()
with sftp.open('/config/lovelace','r') as f:lovelace=f.read().decode()
sftp.close()

# Check for key content markers
markers=['基础倍率设置','孤岛-英灵殿','采集倍率','经验获取速查']
print('=== Content markers in lovelace ===')
for m in markers:
    n=lovelace.count(m)
    print('  {}: {}'.format(m,n))

# Check for old-format markers
old_markers=['loadTribeOps','renderTribeOps','Asd']
print('\n=== Old/dead markers ===')
for m in old_markers:
    n=lovelace.count(m)
    print('  {}: {}'.format(m,n))

# Check data file timestamps vs lovelace
sin,sout,serr=ssh.exec_command('stat -c "%n %Y" /config/www/asa-data/server_rules.json /config/www/asa-data/tribe_ops.json /config/www/asa-data/asa_base_quick_ref.json',timeout=10)
print('\n=== Data file timestamps ===')
print(sout.read().decode())

# Check if build_lovelace.py output goes to correct place
sin,sout,serr=ssh.exec_command('grep -n "lovelace_path\|storage_src\|lovelace.lovelace" /config/build_lovelace.py | head -10',timeout=10)
print('=== build_lovelace output paths ===')
print(sout.read().decode())

ssh.close()
