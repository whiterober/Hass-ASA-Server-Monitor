import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
content=content.replace('\r\n','\n')

# R1: Fix comment L1551
old="# Table-level rules (any tab with tabular content — reference_table, mixed_content, server_grid, farming_table)"
new="# Table-level rules (any tab with tabular content — reference_table, mixed_content)"
n=content.count(old)
if n==1: content=content.replace(old,new); print('R1 OK: comment L1551')
elif n==0: print('R1 SKIP')
else: print('R1 FAIL:',n)

# R2: Fix comment L1584
old="/* Generic table styling — matches server_grid / farming_table visuals */"
new="/* Generic table styling */"
n=content.count(old)
if n==1: content=content.replace(old,new); print('R2 OK: comment L1584')
elif n==0: print('R2 SKIP')
else: print('R2 FAIL:',n)

# R3: Delete bbt supply_card block (L2161-L2168)
old="""                elif bbt=='supply_card':
                    fm=blk.get('filter_maps','')
                    if fm: active_maps.update(fm.split(','))
                    items=blk.get('items',[]) if blk.get('items') else ([blk.get('item')] if blk.get('item') else [])
                    for item in items:
                        if item:
                            for sid in item.get('locations',{}).keys():
                                active_maps.add(sid)"""
new=""
n=content.count(old)
if n==1: content=content.replace(old,new); print('R3 OK: bbt supply_card (8 lines)')
elif n==0: print('R3 SKIP')
else: print('R3 FAIL:',n)

# R4: Delete bbt expandable_detail block (L2169-L2171)
old="""                elif bbt=='expandable_detail':
                    fm=blk.get('filter_maps','')
                    if fm: active_maps.update(fm.split(','))"""
new=""
n=content.count(old)
if n==1: content=content.replace(old,new); print('R4 OK: bbt expandable_detail (3 lines)')
elif n==0: print('R4 SKIP')
else: print('R4 FAIL:',n)

# R5: Delete card_grid IC_CSS (L3138-L3139)
old="""            if 'card_grid' in block_types:
                css += 'ha-card .info-card{background:var(--primary-background-color);border-radius:8px;overflow:hidden;text-align:center;padding:0 0 8px 0}ha-card .info-card img{width:100%;aspect-ratio:1;object-fit:cover}ha-card .card-name{font-weight:600;margin:4px 0}ha-card .card-feature{font-size:0.85em;color:var(--secondary-text-color)}ha-card .card-grid{display:grid;gap:12px}'"""
new=""
n=content.count(old)
if n==1: content=content.replace(old,new); print('R5 OK: card_grid IC_CSS')
elif n==0: print('R5 SKIP')
else: print('R5 FAIL:',n)

# Verify and upload
content_final=content.replace('\n','\r\n')
sftp=c.open_sftp()
with sftp.open('/tmp/_clean3.py','w') as f:f.write(content_final)
sftp.close()
sin,sout,serr=c.exec_command('python3 -c "compile(open(\'/tmp/_clean3.py\').read(),\'/tmp/_clean3.py\',\'exec\')" 2>&1; echo "EXIT:$?"',timeout=10)
out=sout.read().decode()
if 'EXIT:0' in out and 'SyntaxError' not in out:
    print('\nSyntax: OK')
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(content_final)
    sftp.close()
    print('Chars: {} -> {}'.format(len(orig),len(content_final)))
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null',timeout=10)
    out2=sout.read().decode().strip()
    print('Preview:', 'OK' if 'written' in out2.lower() else out2[:150])
    for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
        n=content_final.count(kw)
        if n>0: print('  {}: {} refs'.format(kw,n))
else:
    print('Syntax FAIL:',out[:300])
c.close()
