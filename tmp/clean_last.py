import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:c=f.read().decode()
sftp.close()
c=c.replace('\r\n','\n')

# Find render_farming_table - from def to next top-level def (excluding itself)
m=re.search(r'\ndef render_farming_table\(tab\):.*?(?=\ndef (?!render_farming_table)[a-z_])',c,re.DOTALL)
if m:
    block=m.group(0)
    print('Found:',len(block),'chars, unique:',c.count(block))
    c=c.replace(block,'')
    print('After delete:',len(c),'chars')
    print('farming_table refs:',c.count('farming_table'))
    
    cf=c.replace('\n','\r\n')
    sftp=ssh.open_sftp()
    with sftp.open('/tmp/_cf.py','w') as f:f.write(cf)
    sftp.close()
    sin,sout,serr=ssh.exec_command('python3 -m py_compile /tmp/_cf.py 2>&1; echo E:$?',timeout=10)
    r=sout.read().decode()
    if 'E:0' in r:
        print('Syntax: OK')
        sftp=ssh.open_sftp()
        with sftp.open('/config/build_lovelace.py','w') as f:f.write(cf)
        sftp.close()
        sin,sout,serr=ssh.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>/dev/null; echo E:$?',timeout=15)
        r2=sout.read().decode()
        if 'E:0' in r2:
            print('Preview: OK')
            for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
                n=cf.count(kw)
                if n>0: print('  {}: {} refs'.format(kw,n))
            if all(cf.count(k)==0 for k in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']):
                print('ALL CLEAN! Zero refs.')
        else:
            print('Preview FAIL:',r2[-200:])
    else:
        print('Syntax FAIL:',r[:200])
else:
    print('render_farming_table NOT FOUND')
ssh.close()
