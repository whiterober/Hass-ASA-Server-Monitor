import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
ssh.close()
content=content.replace('\r\n','\n')

def find_block(content, pattern, end_patterns):
    m=re.search(pattern, content)
    if not m: return None,0
    start=m.start()
    rest=content[m.end():]
    end_pos=len(rest)
    for ep in end_patterns:
        em=re.search(ep, rest)
        if em and em.start()<end_pos:
            end_pos=em.start()
    block=content[start:m.end()+end_pos]
    count=content.count(block)
    return block,count

blocks=[]
for name,pat,ends in [
    ('bt supply_card',r'\n            elif bt==.supply_card.:',[r'\n            elif bt==.',r'\n            else:',r'\n        elif ttype',r'\n    parts\.append']),
    ('bt server_grid',r'\n            elif bt==.server_grid.:',[r'\n            elif bt==.',r'\n            else:',r'\n        elif ttype',r'\n    parts\.append']),
    ('bt card_grid',r'\n            elif bt==.card_grid.:',[r'\n            elif bt==.',r'\n            else:',r'\n        elif ttype',r'\n    parts\.append']),
    ('bt expandable_detail',r'\n            elif bt==.expandable_detail.:',[r'\n            elif bt==.',r'\n            else:',r'\n        elif ttype',r'\n    parts\.append']),
    ('ttype farming_table',r'\n    elif ttype == .farming_table.:',[r'\n    elif ttype == ',r'\n    parts\.append\(\'</div>\'\)',r'\ndef render_']),
]:
    block,cnt=find_block(content,pat,ends)
    if cnt==1:
        blocks.append((name,block))
        print('{}: {} chars, unique'.format(name,len(block)))
    elif cnt==0:
        print('{}: NOT FOUND'.format(name))
    else:
        print('{}: {} occurrences, NOT unique'.format(name,cnt))

# render_farming_table
m=re.search(r'\ndef render_farming_table\(tab\):', content)
if m:
    start=m.start()+1
    rest=content[start:]
    em=re.search(r'\ndef [a-z_]', rest)
    if em:
        block=content[start:start+em.start()]
        cnt=content.count(block)
        print('render_farming_table: {} chars, {} occurrences'.format(len(block),cnt))
        if cnt==1: blocks.append(('render_farming_table',block))

# Apply deletions
for name,block in blocks:
    content=content.replace(block,'')
    print('Deleted: {} ({} chars)'.format(name,len(block)))

# Verify
content_final=content.replace('\n','\r\n')
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/tmp/_clean_final.py','w') as f:f.write(content_final)
sftp.close()
sin,sout,serr=ssh.exec_command('python3 -c "compile(open(\'/tmp/_clean_final.py\').read(),\'/tmp/_clean_final.py\',\'exec\')" 2>&1; echo "EXIT:$?"',timeout=10)
out=sout.read().decode()
if 'EXIT:0' in out and 'SyntaxError' not in out:
    print('\nSyntax: OK')
    sftp=ssh.open_sftp()
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(content_final)
    sftp.close()
    sin,sout,serr=ssh.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null; echo "EXIT:$?"',timeout=15)
    out2=sout.read().decode()
    if 'EXIT:0' in out2:
        print('Preview: OK')
        for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
            n=content_final.count(kw)
            if n>0: print('  {}: {} refs'.format(kw,n))
        if all(content_final.count(k)==0 for k in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']):
            print('ALL CLEAN!')
    else:
        print('Preview FAIL:', out2[-200:])
else:
    print('Syntax FAIL:', out[:300])
ssh.close()
