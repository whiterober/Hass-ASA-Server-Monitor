import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
content=content.replace('\r\n','\n')

# Find and delete render_server_grid
m=re.search(r'\n(def render_server_grid\(tab\):.*?)(?=\n\ndef )', content, re.DOTALL)
if m and content.count(m.group(1))==1:
    content=content.replace(m.group(1),'')
    print('R6 OK: render_server_grid ({} chars)'.format(len(m.group(1))))

# Find and delete render_expandable_detail
m=re.search(r'\n(def render_expandable_detail\(tab\):.*?)(?=\n\ndef )', content, re.DOTALL)
if m and content.count(m.group(1))==1:
    content=content.replace(m.group(1),'')
    print('R7 OK: render_expandable_detail ({} chars)'.format(len(m.group(1))))

# Verify
content_final=content.replace('\n','\r\n')
sftp=c.open_sftp()
with sftp.open('/tmp/_clean4.py','w') as f:f.write(content_final)
sftp.close()
sin,sout,serr=c.exec_command('python3 -c "compile(open(\'/tmp/_clean4.py\').read(),\'/tmp/_clean4.py\',\'exec\')" 2>&1; echo "EXIT:$?"',timeout=10)
out=sout.read().decode()
if 'EXIT:0' in out and 'SyntaxError' not in out:
    print('Syntax: OK')
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
