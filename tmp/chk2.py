import paramiko,os,hashlib
def md5(d):
    import hashlib
    return hashlib.md5(d.encode() if isinstance(d,str) else d).hexdigest()[:12]

# Server
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:srv_pr=f.read().decode()
with sftp.open('/config/build_lovelace.py','r') as f:srv_bl=f.read().decode()
sftp.close()

# Local workspace root
ws_pr_path=r'b:\项目\Hass ASA Server Monitor\preview_server.py'
ws_bl_path=r'b:\项目\Hass ASA Server Monitor\build_lovelace.py'
with open(ws_pr_path,'r',encoding='utf-8') as f:ws_pr=f.read()
with open(ws_bl_path,'r',encoding='utf-8') as f:ws_bl=f.read()

# Backup
bak_pr_path=r'c:\Users\white\.copilot\bak\asa_v1337b_20260714\preview_server.py'
bak_bl_path=r'c:\Users\white\.copilot\bak\asa_v1337b_20260714\build_lovelace.py'
with open(bak_pr_path,'r',encoding='utf-8') as f:bak_pr=f.read()
with open(bak_bl_path,'r',encoding='utf-8') as f:bak_bl=f.read()

print('=== preview_server.py ===')
print('Server:    {:>6} chars  MD5={}  render_server_grid in import: {}'.format(len(srv_pr),md5(srv_pr),'render_server_grid' in srv_pr[:300]))
print('Workspace: {:>6} chars  MD5={}  render_server_grid in import: {}'.format(len(ws_pr),md5(ws_pr),'render_server_grid' in ws_pr[:300]))
print('Backup:    {:>6} chars  MD5={}  render_server_grid in import: {}'.format(len(bak_pr),md5(bak_pr),'render_server_grid' in bak_pr[:300]))
print()
m='SAME' if srv_pr==ws_pr else 'DIFF ({})'.format('server newer' if len(srv_pr)>len(ws_pr) else 'ws newer')
print('Server vs Workspace: {}'.format(m))
m='SAME' if srv_pr==bak_pr else 'DIFF'
print('Server vs Backup: {}'.format(m))

print()
print('=== build_lovelace.py ===')
print('Server:    {:>6} chars  MD5={}  render_svr={} render_exp={}'.format(len(srv_bl),md5(srv_bl),srv_bl.count('def render_server_grid'),srv_bl.count('def render_expandable_detail')))
print('Workspace: {:>6} chars  MD5={}  render_svr={} render_exp={}'.format(len(ws_bl),md5(ws_bl),ws_bl.count('def render_server_grid'),ws_bl.count('def render_expandable_detail')))
print('Backup:    {:>6} chars  MD5={}  render_svr={} render_exp={}'.format(len(bak_bl),md5(bak_bl),bak_bl.count('def render_server_grid'),bak_bl.count('def render_expandable_detail')))
print()
m='SAME' if srv_bl==ws_bl else 'DIFF ({})'.format('server newer' if len(srv_bl)>len(ws_bl) else 'ws newer')
print('Server vs Workspace: {}'.format(m))
c.close()
