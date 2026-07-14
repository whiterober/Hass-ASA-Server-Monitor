"""Final cleanup v2: handle CRLF line endings"""
import paramiko

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
print(f'Original: {len(content)} chars, CRLF count: {content.count(chr(13)+chr(10))}')

# Normalize line endings for matching
content_norm=content.replace('\r\n','\n')

# R1: Main dispatch
old="""        if ttype == 'server_grid':
            t_html = render_server_grid(t)
        elif ttype == 'expandable_detail':
            t_html = render_expandable_detail(t)
        elif ttype == 'farming_table':
            t_html = render_farming_table(t)
        else:
            t_html = render_tab_html(t)"""
new="""        t_html = render_tab_html(t)"""
n=content_norm.count(old)
if n==1: content_norm=content_norm.replace(old,new); print('R1 OK')
elif n==0: print('R1 SKIP')
else: print(f'R1 FAIL: {n}')

# R2: IC_CSS tab_type
old="""        elif tab_type == 'server_grid':
            css = SERVER_GRID_CSS
        elif tab_type == 'expandable_detail':
            css = EXPANDABLE_DETAIL_CSS
        elif tab_type == 'farming_table':
            css = FARMING_TABLE_CSS"""
new=""
n=content_norm.count(old)
if n==1: content_norm=content_norm.replace(old,new); print('R2 OK')
elif n==0: print('R2 SKIP')
else: print(f'R2 FAIL: {n}')

# R3: IC_CSS block_types
old="""            if 'server_grid' in block_types:
                css = SERVER_GRID_CSS  # includes SHARED_CSS
            if 'expandable_detail' in block_types:
                css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')"""
new=""
n=content_norm.count(old)
if n==1: content_norm=content_norm.replace(old,new); print('R3 OK')
elif n==0: print('R3 SKIP')
else: print(f'R3 FAIL: {n}')

# R4: IC_CSS bbt
old="""                    elif bbt == 'supply_card':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                    elif bbt == 'expandable_detail':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))"""
new=""
n=content_norm.count(old)
if n==1: content_norm=content_norm.replace(old,new); print('R4 OK')
elif n==0: print('R4 SKIP')
else: print(f'R4 FAIL: {n}')

# R5: supply_card condition
old="""            if 'supply_card' in block_types or 'map_filter' in block_types:"""
new="""            if 'map_filter' in block_types:"""
n=content_norm.count(old)
if n==1: content_norm=content_norm.replace(old,new); print('R5 OK')
elif n==0: print('R5 SKIP')
else: print(f'R5 FAIL: {n}')

# Restore CRLF
content_final=content_norm.replace('\n','\r\n')

# Verify syntax
sftp=c.open_sftp()
with sftp.open('/tmp/_fc2.py','w') as f:f.write(content_final)
sftp.close()

sin,sout,serr=c.exec_command('python3 -c "compile(open(\'/tmp/_fc2.py\').read(),\'/tmp/_fc2.py\',\'exec\')" 2>&1; echo "EXIT:$?"',timeout=10)
out=sout.read().decode()
if 'EXIT:0' in out and 'SyntaxError' not in out:
    print('\nSyntax: OK')
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(content_final)
    sftp.close()
    print(f'Uploaded: {len(orig)} -> {len(content_final)} chars')
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null',timeout=10)
    out2=sout.read().decode().strip()
    print('Preview:', 'OK' if 'written' in out2.lower() else out2[:150])
    
    for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
        n=content_final.count(kw)
        if n>0: print(f'  {kw}: {n} refs left')
else:
    print('\nSyntax FAIL:', out[:300])
c.close()
