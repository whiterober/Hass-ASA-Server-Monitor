import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()

lines=content.split('\n')
orig_count=len(lines)

# Delete in reverse order (bottom to top) to avoid line shifts
deletions=[
    # (start_line_1based, end_line_1based, description)
    (3276,3281,'main dispatch: server_grid/expandable_detail/farming_table'),
    (3148,3153,'IC_CSS tab_type: server_grid/expandable_detail/farming_table'),
    (3089,3092,'IC_CSS block_types: server_grid + expandable_detail conditions'),
    (3081,3086,'IC_CSS bbt: supply_card + expandable_detail filter_maps'),
]

for s,e,desc in sorted(deletions,reverse=True):
    del_lines=lines[s-1:e]
    print(f'Delete L{s}-L{e} ({e-s+1} lines): {desc}')
    for l in del_lines:
        print(f'  {l[:100]}')
    lines[s-1:e]=[]

# Fix supply_card condition
for i,l in enumerate(lines):
    if "'supply_card' in block_types or 'map_filter' in block_types" in l:
        old=l
        new=l.replace("'supply_card' in block_types or ","")
        lines[i]=new
        print(f'\nFix L{i+1}: supply_card condition')
        print(f'  OLD: {old.strip()[:100]}')
        print(f'  NEW: {new.strip()[:100]}')
        break

new_content='\n'.join(lines)
print(f'\nLines: {orig_count} -> {len(lines)} (diff: {len(lines)-orig_count})')

# Verify syntax
sftp=c.open_sftp()
with sftp.open('/tmp/_clean2.py','w') as f:f.write(new_content)
sftp.close()
sin,sout,serr=c.exec_command('python3 -m py_compile /tmp/_clean2.py 2>&1 && echo SYNTAX_OK || echo SYNTAX_FAIL',timeout=10)
r=sout.read().decode().strip()
print('Syntax:', 'OK' if 'SYNTAX_OK' in r else r[:200])

if 'SYNTAX_OK' in r:
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(new_content)
    sftp.close()
    print('Uploaded!')
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null',timeout=10)
    out=sout.read().decode().strip()
    print('Preview:', 'OK' if 'written' in out.lower() else out[:150])
c.close()
