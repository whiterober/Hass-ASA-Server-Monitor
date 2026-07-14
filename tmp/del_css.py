import paramiko,re
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
bl_n=bl.replace('\r\n','\n')

# Find all _CSS =  definitions
for m in re.finditer(r'^(\w+_CSS)\s*=',bl_n,re.MULTILINE):
    name=m.group(1)
    start=m.start()
    # Find closing """ or end of string
    rest=bl_n[start:]
    end_m=re.search(r'"""',rest[rest.index('=')+1:])
    if end_m:
        # Find next non-empty line after closing """
        after_close=rest.index('=')+1+end_m.start()+3
        end=start+after_close
        # Go to next newline
        nl=bl_n.find('\n',end)
        print('{}: {} chars ({}..{})'.format(name,end-start,start,nl))

# Now delete all three dead ones
dead=['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS']
for name in dead:
    # Find the constant - from name= to the end of its """ block
    m=re.search(name+r'\s*=\s*SHARED_CSS\s*\+\s*""".*?"""',bl_n,re.DOTALL)
    if m:
        block=m.group()
        # Include trailing newline
        full=block+'\n'
        c=bl_n.count(full)
        print('\n{}: {} chars, unique: {}'.format(name,len(full),c))
        if c==1:
            bl_n=bl_n.replace(full,'')
            print('  Deleted')
    else:
        # Try without SHARED_CSS +
        m=re.search(name+r'\s*=\s*""".*?"""',bl_n,re.DOTALL)
        if m:
            print('\n{}: standalone, {} chars'.format(name,len(m.group())))
        else:
            print('\n{}: NOT FOUND'.format(name))

print('\nNew size: {} chars'.format(len(bl_n)))
ssh.close()
