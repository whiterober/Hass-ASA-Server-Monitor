import paramiko,os,shutil

def fmt_diff(new,old):
    d=new-old
    pct=abs(d)/old*100
    if d<0: return '-{:,} ({:.1f}%)'.format(-d,pct)
    return '+{:,} (+{:.1f}%)'.format(d,pct)

# Current server files
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:now_bl_data=f.read()
with sftp.open('/config/preview_server.py','r') as f:now_pr_data=f.read()
sftp.close()
c.close()
now_bl=len(now_bl_data)
now_pr=len(now_pr_data)

# v1316 baseline
bak=r'c:\Users\white\.copilot\bak'
v1316_bl=os.path.getsize(os.path.join(bak,'build_lovelace_baseline_v1316_20260714_154742'))
v1316_pr=os.path.getsize(os.path.join(bak,'preview_server_baseline_v1316_20260714_154742'))
v1316_html=os.path.getsize(os.path.join(bak,'asa-admin_baseline_v1316_20260714_154742'))
now_html=os.path.getsize(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html')

print('=== build_lovelace.py ===')
print('  v1316: {:>7,} bytes'.format(v1316_bl))
print('  NOW:   {:>7,} bytes ({})'.format(now_bl,fmt_diff(now_bl,v1316_bl)))
print('\n=== preview_server.py ===')
print('  v1316: {:>7,} bytes'.format(v1316_pr))
print('  NOW:   {:>7,} bytes ({})'.format(now_pr,fmt_diff(now_pr,v1316_pr)))
print('\n=== asa-admin.html ===')
print('  v1316: {:>7,} bytes'.format(v1316_html))
print('  NOW:   {:>7,} bytes ({})'.format(now_html,fmt_diff(now_html,v1316_html)))
total_old=v1316_bl+v1316_pr+v1316_html
total_new=now_bl+now_pr+now_html
print('\n=== TOTAL ===')
print('  v1316: {:>7,} bytes'.format(total_old))
print('  NOW:   {:>7,} bytes'.format(total_new))
print('  Reduction: {:,} bytes ({:.1f} KB = {:.1%})'.format(total_old-total_new,(total_old-total_new)/1024,(total_old-total_new)/total_old))

# Backup new baseline
bak_dir=os.path.join(bak,'asa_v1337c_20260714')
os.makedirs(bak_dir,exist_ok=True)
h='192.168.197.253'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
files=[('/config/lovelace','lovelace'),('/config/lovelace.lovelace','lovelace.lovelace'),
       ('/config/www/asa-data/server_rules.json','server_rules.json'),
       ('/config/www/asa-data/tribe_ops.json','tribe_ops.json'),
       ('/config/www/asa-data/asa_base_quick_ref.json','asa_base_quick_ref.json')]
for r,l in files:
    try:
        with sftp.open(r,'r') as f:data=f.read()
        with open(os.path.join(bak_dir,l),'wb') as f:f.write(data)
        print('OK: {} ({} bytes)'.format(l,len(data)))
    except Exception as e:print('FAIL: {} {}'.format(l,e))
sftp.close()
# Local files
for src,dst in [('build_lovelace.py','build_lovelace.py'),('preview_server.py','preview_server.py'),
                 (r'www\asa-admin.html','asa-admin.html')]:
    sp=os.path.join(r'b:\项目\Hass ASA Server Monitor',src)
    dp=os.path.join(bak_dir,dst)
    shutil.copy2(sp,dp)
    print('OK: {} ({} bytes)'.format(dst,os.path.getsize(dp)))
print('\nBackup: {} files in {}'.format(len(os.listdir(bak_dir)),bak_dir))
