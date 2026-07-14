import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
sftp.close()

print('=== build_lovelace.py functions ===')
for fn in ['make_ic_css','render_tab_html','_lookup_style','strip_and_append_empty_rows',
           'render_server_grid','render_expandable_detail','render_farming_table']:
    defs=len(re.findall(r'\ndef '+fn+r'\b',bl))
    calls=max(0,len(re.findall(fn+r'\b',bl))-defs)
    status='DEAD?' if calls==0 and defs>0 else ''
    if defs>0:print('  {}: {} def, {} calls {}'.format(fn,defs,calls,status))

print('\n=== CSS constants (build_lovelace.py) ===')
for cc in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS',
           'SHARED_CSS','BASE_RAW_CSS','TABLE_CORE_CSS','CARD_CORE_CSS']:
    n=bl.count(cc)
    if n>0:print('  {}: {} refs'.format(cc,n))

print('\n=== preview_server.py imports ===')
pr=pr.replace('\r\n','\n')
imp=re.search(r'from build_lovelace import \((.*?)\)',pr,re.DOTALL)
if imp:
    imported=[x.strip() for x in imp.group(1).split(',') if x.strip()]
    for name in imported:
        used=max(0,pr.count(name)-1)
        status='UNUSED!' if used==0 else ''
        print('  {}: used {} times in body {}'.format(name,used,status))

print('\n=== asa-admin.html dead patterns ===')
html=open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html',encoding='utf-8').read()
for pat in ['copyBRFrom','loadTribeOps','console\\.log','debugger']:
    n=len(re.findall(pat,html))
    if n>0:print('  {}: {} occurrences'.format(pat,n))

ssh.close()
