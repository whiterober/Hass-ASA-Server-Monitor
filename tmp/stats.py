import paramiko,os

# Current server files
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:now_bl=len(f.read().decode())
with sftp.open('/config/preview_server.py','r') as f:now_pr=len(f.read().decode())
sftp.close()
c.close()

# v1316 baseline
bak=r'c:\Users\white\.copilot\bak'
with open(os.path.join(bak,'build_lovelace_baseline_v1316_20260714_154742'),'rb') as f:v1316_bl=len(f.read())
with open(os.path.join(bak,'preview_server_baseline_v1316_20260714_154742'),'rb') as f:v1316_pr=len(f.read())
with open(os.path.join(bak,'asa-admin_baseline_v1316_20260714_154742'),'rb') as f:v1316_html=len(f.read())

# Current asa-admin.html (local workspace)
now_html=os.path.getsize(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html')

# Also check v1337b backup for comparison
v1337b_bl=os.path.getsize(os.path.join(bak,'asa_v1337b_20260714','build_lovelace.py'))
v1337b_pr=os.path.getsize(os.path.join(bak,'asa_v1337b_20260714','preview_server.py'))

print('=== build_lovelace.py ===')
print('  v1316: {:>7,} bytes'.format(v1316_bl))
print('  v1337b:{:>7,} bytes ({})'.format(v1337b_bl, fmt_diff(v1337b_bl,v1316_bl)))
print('  NOW:   {:>7,} bytes ({})'.format(now_bl, fmt_diff(now_bl,v1316_bl)))

print('\n=== preview_server.py ===')
print('  v1316: {:>7,} bytes'.format(v1316_pr))
print('  v1337b:{:>7,} bytes ({})'.format(v1337b_pr, fmt_diff(v1337b_pr,v1316_pr)))
print('  NOW:   {:>7,} bytes ({})'.format(now_pr, fmt_diff(now_pr,v1316_pr)))

print('\n=== asa-admin.html ===')
print('  v1316: {:>7,} bytes'.format(v1316_html))
print('  NOW:   {:>7,} bytes ({})'.format(now_html, fmt_diff(now_html,v1316_html)))

# Total
total_old=v1316_bl+v1316_pr+v1316_html
total_new=now_bl+now_pr+now_html
print('\n=== TOTAL (BL + PR + HTML) ===')
print('  v1316: {:>7,} bytes'.format(total_old))
print('  NOW:   {:>7,} bytes ({})'.format(total_new, fmt_diff(total_new,total_old)))
print('  Reduction: {:,} bytes ({:.1f} KB / {:.1%})'.format(total_old-total_new,(total_old-total_new)/1024,(total_old-total_new)/total_old))
