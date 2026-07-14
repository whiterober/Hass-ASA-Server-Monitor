import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Read and clean build_lovelace.py
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
bl_n=bl.replace('\r\n','\n')

# Delete 3 dead CSS constants
for name in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS']:
    m=re.search(name+r'\s*=\s*SHARED_CSS\s*\+\s*""".*?"""\n',bl_n,re.DOTALL)
    if m and bl_n.count(m.group())==1:
        bl_n=bl_n.replace(m.group(),'')
        print('Deleted: {} ({} chars)'.format(name,len(m.group())))

# Upload and verify
bl_final=bl_n.replace('\n','\r\n')
sftp=ssh.open_sftp()
with sftp.open('/tmp/_css_clean.py','w') as f:f.write(bl_final)
sftp.close()
sin,sout,serr=ssh.exec_command('python3 -m py_compile /tmp/_css_clean.py 2>&1; echo E:$?',timeout=10)
r=sout.read().decode()
if 'E:0' in r and 'Error' not in r:
    sftp=ssh.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(bl_final)
    sftp.close()
    print('Syntax OK, uploaded: {} chars'.format(len(bl_final)))
    
    # Clean preview_server.py
    sftp=ssh.open_sftp()
    with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
    sftp.close()
    pr_n=pr.replace('\r\n','\n')
    # Remove _lookup_style from import
    old=', _lookup_style'
    if old in pr_n:
        pr_n=pr_n.replace(old,'')
        pr_final=pr_n.replace('\n','\r\n')
        sftp=ssh.open_sftp()
        with sftp.open('/config/preview_server.py','w') as f:f.write(pr_final)
        sftp.close()
        print('Removed _lookup_style from preview_server.py')

    # Test preview
    sin,sout,serr=ssh.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>/dev/null; echo E:$?',timeout=15)
    r2=sout.read().decode()
    if 'E:0' in r2:
        print('Preview: OK')
        # Count remaining
        for kw in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS']:
            n=bl_final.count(kw)
            if n>0:print('  {}: {} refs'.format(kw,n))
        if all(bl_final.count(k)==0 for k in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS']):
            print('  ALL CLEAN!')
    else:
        print('Preview FAIL:',r2[-200:])
else:
    print('Syntax FAIL:',r[:300])
ssh.close()
