import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:c=f.read().decode()
sftp.close()
c_orig=c
c=c.replace('\r\n','\n')

# Find all top-level def positions
defs=[]
for m in re.finditer(r'^def [a-z_]', c, re.MULTILINE):
    defs.append((m.start(), c[m.start():m.start()+40]))

# Find render_farming_table and next def
rft_start=None
for i,(pos,name) in enumerate(defs):
    if 'render_farming_table' in name:
        rft_start=pos
        rft_idx=i
        break

if rft_start:
    # Next def after render_farming_table
    next_def_pos=defs[rft_idx+1][0] if rft_idx+1<len(defs) else len(c)
    block=c[rft_start:next_def_pos].rstrip('\n')
    print('render_farming_table: {} chars, starts with: {}'.format(len(block),block[:60]))
    print('Unique:', c_orig.count(block))
    
    # Delete
    c=c.replace('\n'+block, '')
    cf=c.replace('\n','\r\n')
    
    sftp=ssh.open_sftp()
    with sftp.open('/tmp/_cf2.py','w') as f:f.write(cf)
    sftp.close()
    sin,sout,serr=ssh.exec_command('python3 -m py_compile /tmp/_cf2.py 2>&1; echo E:$?',timeout=10)
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
                if n>0: print('  {}: {}'.format(kw,n))
            if all(cf.count(k)==0 for k in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']):
                print('ALL CLEAN!')
        else:
            print('Preview FAIL:',r2[-200:])
    else:
        print('Syntax FAIL:',r[:200])
else:
    print('NOT FOUND')
    print('All top-level defs:')
    for pos,name in defs[:10]:
        print('  {}: {}'.format(pos,name.strip()))
ssh.close()
