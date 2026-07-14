"""Final cleanup: exact string replacements via paramiko"""
import paramiko

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Step 1: Read server file
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
print(f'Original: {len(content)} chars, {len(content.splitlines())} lines')

# Step 2: Apply replacements (most impactful first)
# These are verified exact strings from the server file

# R1: Main dispatch - replace if/elif chain with just else body
old="""        if ttype == 'server_grid':
            t_html = render_server_grid(t)
        elif ttype == 'expandable_detail':
            t_html = render_expandable_detail(t)
        elif ttype == 'farming_table':
            t_html = render_farming_table(t)
        else:
            t_html = render_tab_html(t)"""
new="""        t_html = render_tab_html(t)"""
n=content.count(old)
if n==1:
    content=content.replace(old,new)
    print('R1 OK: main dispatch (if/elif/else -> simple assignment)')
elif n==0:
    print('R1 SKIP: main dispatch not found')
else:
    print(f'R1 FAIL: found {n} matches (not unique)')

# R2: IC_CSS tab_type elif chain
old="""        elif tab_type == 'server_grid':
            css = SERVER_GRID_CSS
        elif tab_type == 'expandable_detail':
            css = EXPANDABLE_DETAIL_CSS
        elif tab_type == 'farming_table':
            css = FARMING_TABLE_CSS"""
new=""
n=content.count(old)
if n==1:
    content=content.replace(old,new)
    print('R2 OK: IC_CSS tab_type elif chain')
elif n==0:
    print('R2 SKIP: not found')
else:
    print(f'R2 FAIL: {n} matches')

# R3: IC_CSS block_types - server_grid + expandable_detail conditions
old="""            if 'server_grid' in block_types:
                css = SERVER_GRID_CSS  # includes SHARED_CSS
            if 'expandable_detail' in block_types:
                css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')"""
new=""
n=content.count(old)
if n==1:
    content=content.replace(old,new)
    print('R3 OK: IC_CSS block_types conditions')
elif n==0:
    print('R3 SKIP: not found')
else:
    print(f'R3 FAIL: {n} matches')

# R4: IC_CSS bbt elif blocks (supply_card + expandable_detail in map filter loop)
old="""                    elif bbt == 'supply_card':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                    elif bbt == 'expandable_detail':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))"""
new=""
n=content.count(old)
if n==1:
    content=content.replace(old,new)
    print('R4 OK: IC_CSS bbt supply_card + expandable_detail')
elif n==0:
    print('R4 SKIP: not found (may already be cleaned or whitespace differs)')
else:
    print(f'R4 FAIL: {n} matches')

# R5: Fix supply_card condition (change to just map_filter)
old="""            if 'supply_card' in block_types or 'map_filter' in block_types:"""
new="""            if 'map_filter' in block_types:"""
n=content.count(old)
if n==1:
    content=content.replace(old,new)
    print('R5 OK: supply_card condition -> map_filter only')
elif n==0:
    print('R5 SKIP: not found')
else:
    print(f'R5 FAIL: {n} matches')

# Step 3: Verify syntax
sftp=c.open_sftp()
with sftp.open('/tmp/_final_clean.py','w') as f:f.write(content)
sftp.close()

sin,sout,serr=c.exec_command('python3 -c "compile(open(\'/tmp/_final_clean.py\').read(),\'/tmp/_final_clean.py\',\'exec\')" 2>&1; echo "EXIT:$?"',timeout=10)
out=sout.read().decode()
err=serr.read().decode()
if 'EXIT:0' in out+err and 'SyntaxError' not in out+err:
    print('\nSyntax: OK')
    # Upload
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(content)
    sftp.close()
    print(f'Uploaded: {len(orig)} -> {len(content)} chars')
    
    # Test preview
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null',timeout=10)
    out2=sout.read().decode().strip()
    if 'written' in out2.lower():
        print('Preview: OK')
    else:
        print('Preview:', out2[:200] if out2 else 'EMPTY')
    
    # Count remaining
    for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
        n=content.count(kw)
        if n>0: print(f'  {kw}: {n} refs left')
else:
    print('\nSyntax FAIL:')
    print(out[:300] if out else '(empty)')
    print(err[:300] if err else '(empty)')

c.close()
