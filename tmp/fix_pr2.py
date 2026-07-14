import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
sftp.close()
pr_n=pr.replace('\r\n','\n')

old="""from build_lovelace import (
    make_ic_css,
    render_farming_table, render_tab_html,
    SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS, strip_and_append_empty_rows,
    SERVER_MAP, FIXED_STYLES_MAP, _lookup_style
)"""
new="""from build_lovelace import (
    make_ic_css,
    render_tab_html,
    SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS, strip_and_append_empty_rows,
    SERVER_MAP, FIXED_STYLES_MAP, _lookup_style
)"""

if pr_n.count(old)==1:
    pr_n=pr_n.replace(old,new)
    pr_final=pr_n.replace('\n','\r\n')
    sftp=ssh.open_sftp()
    with sftp.open('/config/preview_server.py','w') as f:f.write(pr_final)
    sftp.close()
    print('Fixed import')
    
    # Verify
    sin,sout,serr=ssh.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>/dev/null; echo E:$?',timeout=15)
    r=sout.read().decode()
    if 'E:0' in r:
        print('Preview: OK')
        # Count remaining refs
        sftp=ssh.open_sftp()
        with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
        sftp.close()
        all_zero=True
        for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
            n=bl.count(kw)
            if n>0:
                print('  {}: {}'.format(kw,n))
                all_zero=False
        if all_zero: print('ALL CLEAN!')
    else:
        print('Preview FAIL:',r[-200:])
else:
    print('Import not found or not unique:',pr_n.count(old))
ssh.close()
