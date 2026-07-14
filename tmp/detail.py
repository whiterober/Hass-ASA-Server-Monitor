import paramiko,os,glob

bak=r'c:\Users\white\.copilot\bak'
ws=r'b:\项目\Hass ASA Server Monitor\bak'

# Find all baseline directories/files
all_baks=[]
# Directories (v1335, v1336, v1337, v1337b, v1337c)
for d in sorted(os.listdir(bak)):
    dp=os.path.join(bak,d)
    if os.path.isdir(dp) and any(x in d for x in ['v133','v131']):
        all_baks.append(('DIR',d,dp))
# Individual files (v1316)
for f in sorted(os.listdir(bak)):
    if 'v1316' in f and f.endswith('.html'):
        all_baks.append(('V1316',f,bak))

# Workspace directories
for d in sorted(os.listdir(ws)):
    if 'v133' in d:
        all_baks.append(('WS',d,os.path.join(ws,d)))

# Current server
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:srv_bl=len(f.read().decode())
with sftp.open('/config/preview_server.py','r') as f:srv_pr=len(f.read().decode())
sftp.close()
ssh.close()

# Local HTML
now_html=os.path.getsize(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html')

# Collect all file sizes
def get_size(path,fname):
    try:
        fp=os.path.join(path,fname)
        return os.path.getsize(fp) if os.path.exists(fp) else None
    except:return None

print('=== baselines ===')
for typ,name,path in all_baks:
    if typ=='V1316':continue
    bl=get_size(path,'build_lovelace.py')
    pr=get_size(path,'preview_server.py')
    html=get_size(path,'asa-admin.html')
    if bl:print('{}: bl={} pr={} html={}'.format(name,bl,pr,html))

# v1316
v1316_bl=get_size(bak,'build_lovelace_baseline_v1316_20260714_154742')
v1316_pr=get_size(bak,'preview_server_baseline_v1316_20260714_154742')
v1316_html=get_size(bak,'asa-admin_baseline_v1316_20260714_154742')

print('\n=== v1316 → NOW ===')
print('v1316:  bl={} pr={} html={} total={}'.format(v1316_bl,v1316_pr,v1316_html,v1316_bl+v1316_pr+v1316_html))
print('NOW:    bl={} pr={} html={} total={}'.format(srv_bl,srv_pr,now_html,srv_bl+srv_pr+now_html))
d_bl=v1316_bl-srv_bl
d_pr=v1316_pr-srv_pr
d_html=v1316_html-now_html
print('DELTA:  bl={} ({:.1f}%) pr={} ({:.1f}%) html={} ({:.1f}%) total={} ({:.1f}%)'.format(
    d_bl,d_bl/v1316_bl*100,d_pr,d_pr/v1316_pr*100,d_html,d_html/v1316_html*100,
    d_bl+d_pr+d_html,(d_bl+d_pr+d_html)/(v1316_bl+v1316_pr+v1316_html)*100))

# Detail per file
print('\n=== build_lovelace.py detail ===')
prev=v1316_bl
for name,path in [('v1335','asa_v1335_20260714'),('v1336','asa_v1336_20260714'),
                   ('v1337','asa_v1337_20260714'),('v1337b','asa_v1337b_20260714'),
                   ('v1337c','asa_v1337c_20260714')]:
    for loc in [bak,ws]:
        fp=os.path.join(loc,path,'build_lovelace.py')
        if os.path.exists(fp):
            sz=os.path.getsize(fp)
            d=sz-prev
            print('  {}: {:>6,} ({})'.format(name,sz,'+' if d>=0 else '')+str(d))
            prev=sz
            break
print('  NOW: {:>6,} ({})'.format(srv_bl,'+' if srv_bl-prev>=0 else '')+str(srv_bl-prev))
