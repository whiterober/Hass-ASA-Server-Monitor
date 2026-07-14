import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
orig=content
content=content.replace('\r\n','\n')

# Find render function boundaries
lines=content.split('\n')
for func_name in ['render_server_grid','render_expandable_detail','render_farming_table']:
    start=None;end=None
    for i,l in enumerate(lines):
        if l.strip().startswith('def '+func_name+'('):
            start=i
        if start is not None and i>start and l.strip()=='' and i+1<len(lines):
            nl=lines[i+1].strip()
            if nl.startswith('def ') or nl.startswith('class ') or nl.startswith('# ===') or nl.startswith('_log_step'):
                end=i
                break
    if start is not None and end is None:
        end=len(lines)-1
    if start is not None:
        print('{}: L{}-L{} ({} lines)'.format(func_name,start+1,end+1,end-start+1))
        # Show first and last 3 lines
        for j in range(start,min(start+3,end+1)):
            print('  L{}: {}'.format(j+1,lines[j][:100]))
        for j in range(max(start+3,end-2),end+1):
            print('  L{}: {}'.format(j+1,lines[j][:100]))
c.close()
