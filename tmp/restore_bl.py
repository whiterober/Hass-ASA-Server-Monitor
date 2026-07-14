import paramiko,re,os

# Read v1337c baseline (has build() function)
v1337c_path=r'c:\Users\white\.copilot\bak\asa_v1337c_20260714\build_lovelace.py'
with open(v1337c_path,'r',encoding='utf-8') as f:bl=f.read()

print('v1337c: {} chars'.format(len(bl)))

# Clean only the 3 dead CSS constants (safe operation)
bl_n=bl.replace('\r\n','\n')

cleaned=0
for name in ['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS']:
    m=re.search(name+r'\s*=\s*SHARED_CSS\s*\+\s*""".*?"""\n',bl_n,re.DOTALL)
    if m and bl_n.count(m.group())==1:
        bl_n=bl_n.replace(m.group(),'')
        cleaned+=1
        print('Deleted: {} ({} chars)'.format(name,len(m.group())))
    else:
        print('SKIP: {} (count={})'.format(name,bl_n.count(m.group()) if m else 'not found'))

print('\nAfter cleanup: {} chars'.format(len(bl_n)))

# Verify build() is intact
for pat in ['def build\\(','if __name__','_log_step','SAVED_OK']:
    n=bl_n.count(pat)
    print('  {}: {}'.format(pat,n))

# Restore CRLF and upload
bl_final=bl_n.replace('\n','\r\n')

ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Test syntax
sftp=ssh.open_sftp()
with sftp.open('/tmp/_restored.py','w') as f:f.write(bl_final)
sftp.close()
sin,sout,serr=ssh.exec_command('python3 -m py_compile /tmp/_restored.py 2>&1; echo E:$?',timeout=10)
r=sout.read().decode()
if 'E:0' in r and 'Error' not in r:
    sftp=ssh.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(bl_final)
    sftp.close()
    print('\nSyntax OK, uploaded!')
    
    # Run build_lovelace.py to rebuild lovelace
    sin,sout,serr=ssh.exec_command('cd /config && python3 build_lovelace.py 2>&1; echo E:$?',timeout=30)
    out=sout.read().decode()
    if 'SAVED_OK' in out:
        print('BUILD SUCCESS: SAVED_OK!')
    else:
        print('Build output:',out[-200:] if out else 'EMPTY')
    
    # Check _bl_step.txt
    sin,sout,serr=ssh.exec_command('cat /config/www/asa-data/_bl_step.txt',timeout=10)
    print('_bl_step:',sout.read().decode().strip())
    
    # Check lovelace timestamp
    sin,sout,serr=ssh.exec_command('stat -c "%Y" /config/lovelace',timeout=10)
    print('Lovelace mtime:',sout.read().decode().strip())
else:
    print('Syntax FAIL:',r[:300])

ssh.close()
