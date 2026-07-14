import paramiko
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
sftp.close()
pr_n=pr.replace('\r\n','\n')

old="""from build_lovelace import (
    make_ic_css,
    render_server_grid, render_expandable_detail, render_farming_table, render_tab_html,
    SERVER_GRID_CSS, EXPANDABLE_DETAIL_CSS, FARMING_TABLE_CSS, SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS, strip_and_append_empty_rows,
    SERVER_MAP, FIXED_STYLES_MAP, _lookup_style
)"""
new="""from build_lovelace import (
    make_ic_css,
    render_farming_table, render_tab_html,
    SHARED_CSS,
    CARD_CORE_CSS, TABLE_CORE_CSS, BASE_RAW_CSS, strip_and_append_empty_rows,
    SERVER_MAP, FIXED_STYLES_MAP, _lookup_style
)"""

print('Count:', pr_n.count(old))
if pr_n.count(old)==1:
    pr_n=pr_n.replace(old,new)
    pr_final=pr_n.replace('\n','\r\n')
    sftp=c.open_sftp()
    with sftp.open('/config/preview_server.py','w') as f:f.write(pr_final)
    sftp.close()
    print('Fixed!')
    
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py 0 base_quick_ref 2>&1 | tail -3',timeout=15)
    out=sout.read().decode().strip()
    print(out[-300:] if len(out)>300 else out)
else:
    print('NOT UNIQUE')
c.close()
