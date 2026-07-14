import paramiko,os,hashlib

def md5(data):
    return hashlib.md5(data.encode() if isinstance(data,str) else data).hexdigest()[:12]

# 1. Server files
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:srv_pr=f.read().decode()
with sftp.open('/config/build_lovelace.py','r') as f:srv_bl=f.read().decode()
sftp.close()

# 2. Local backup (v1337b - latest)
bak_dir=r'c:\Users\white\.copilot\bak\asa_v1337b_20260714'
with open(os.path.join(bak_dir,'preview_server.py'),'rb') as f:bak_pr=f.read().decode()
with open(os.path.join(bak_dir,'build_lovelace.py'),'rb') as f:bak_bl=f.read().decode()

# 3. Local workspace
ws_dir=r'b:\项目\Hass ASA Server Monitor'
# Check common locations
ws_paths=[
    os.path.join(ws_dir,'preview_server.py'),
    os.path.join(ws_dir,'bak','asa_v1337b_20260714','preview_server.py'),
]
for p in ws_paths:
    if os.path.exists(p):
        with open(p,'rb') as f:ws_pr=f.read().decode()
        break
else:
    ws_pr=None

ws_bl_path=os.path.join(ws_dir,'bak','asa_v1337b_20260714','build_lovelace.py')
if os.path.exists(ws_bl_path):
    with open(ws_bl_path,'rb') as f:ws_bl=f.read().decode()
else:
    ws_bl=None

print('=== preview_server.py ===')
print('Server: {:>6} chars  MD5={}'.format(len(srv_pr),md5(srv_pr)))
print('Backup: {:>6} chars  MD5={}'.format(len(bak_pr),md5(bak_pr)))
if ws_pr:
    print('Workspace: {:>4} chars  MD5={}'.format(len(ws_pr),md5(ws_pr)))

print()
print('=== build_lovelace.py ===')
print('Server: {:>6} chars  MD5={}'.format(len(srv_bl),md5(srv_bl)))
print('Backup: {:>6} chars  MD5={}'.format(len(bak_bl),md5(bak_bl)))
if ws_bl:
    print('Workspace: {:>4} chars  MD5={}'.format(len(ws_bl),md5(ws_bl)))

print()
# Check key identifiers
for name,content in [('Server PR',srv_pr),('Backup PR',bak_pr)]:
    if 'render_server_grid' in content[:200]: print('{}: OLD import (has render_server_grid)'.format(name))
    elif 'make_ic_css' in content[:200]: print('{}: OK (has make_ic_css)'.format(name))
    else: print('{}: ??? (unexpected import)'.format(name))

for name,content in [('Server BL',srv_bl),('Backup BL',bak_bl)]:
    n=content.count('def render_server_grid')
    print('{}: render_server_grid={}, render_expandable_detail={}, render_farming_table={}'.format(
        name,
        content.count('def render_server_grid'),
        content.count('def render_expandable_detail'),
        content.count('def render_farming_table')))

# Check if server and backup match
print()
if srv_pr==bak_pr: print('preview_server.py: Server == Backup OK')
else: print('preview_server.py: DIFF! Server != Backup')
if srv_bl==bak_bl: print('build_lovelace.py: Server == Backup OK')
else: print('build_lovelace.py: DIFF! Server != Backup')

c.close()
