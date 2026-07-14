import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Check build_lovelace.py CSS constants
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
bl_n=bl.replace('\r\n','\n')

print('=== SERVER_GRID_CSS ===')
m=re.search(r'SERVER_GRID_CSS\s*=\s*"""',bl_n)
if m:
    # Find matching """
    start=m.start()
    end=bl_n.find('"""',m.end())
    end=bl_n.find('\n',end+3)
    constant=bl_n[start:end]
    print('{} chars, unique: {}'.format(len(constant),bl_n.count(constant)))

print('\n=== EXPANDABLE_DETAIL_CSS ===')
m=re.search(r'EXPANDABLE_DETAIL_CSS\s*=\s*"""',bl_n)
if m:
    start=m.start()
    end=bl_n.find('"""',m.end())
    end=bl_n.find('\n',end+3)
    constant=bl_n[start:end]
    print('{} chars, unique: {}'.format(len(constant),bl_n.count(constant)))

print('\n=== FARMING_TABLE_CSS ===')
m=re.search(r'FARMING_TABLE_CSS\s*=\s*"""',bl_n)
if m:
    start=m.start()
    end=bl_n.find('"""',m.end())
    end=bl_n.find('\n',end+3)
    constant=bl_n[start:end]
    print('{} chars, unique: {}'.format(len(constant),bl_n.count(constant)))

# Check preview_server import
sftp=ssh.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
sftp.close()
pr_n=pr.replace('\r\n','\n')
print('\n=== preview_server.py _lookup_style ===')
for i,l in enumerate(pr_n.split('\n'),1):
    if '_lookup_style' in l:
        print('L{}: {}'.format(i,l.strip()))

# Check asa-admin.html
html=open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html',encoding='utf-8').read()
print('\n=== asa-admin.html loadTribeOps ===')
for m in re.finditer(r'.{0,80}loadTribeOps.{0,80}',html):
    print('  ...{}...'.format(m.group().replace('\n',' ')))

print('\n=== asa-admin.html console.log ===')
for m in re.finditer(r'.{0,40}console\.log.{0,60}',html):
    print('  ...{}...'.format(m.group().replace('\n',' ')))

ssh.close()
