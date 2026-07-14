import paramiko,shutil,os

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Pull server files to local workspace
sftp=c.open_sftp()
local_dir=r'b:\项目\Hass ASA Server Monitor'

for remote,local_name in [
    ('/config/preview_server.py','preview_server.py'),
    ('/config/build_lovelace.py','build_lovelace.py'),
]:
    with sftp.open(remote,'r') as f:data=f.read().decode()
    
    # Backup existing local
    local_path=os.path.join(local_dir,local_name)
    if os.path.exists(local_path):
        bak_path=local_path+'.bak_'+'20260714'
        shutil.copy2(local_path,bak_path)
        print('Backup: '+bak_path)
    
    # Write new version (normalize CRLF for Windows)
    with open(local_path,'w',encoding='utf-8',newline='') as f:
        f.write(data)
    print('Updated: {} ({} chars)'.format(local_name,len(data)))

sftp.close()

# Verify
print()
for name in ['preview_server.py','build_lovelace.py']:
    local=open(os.path.join(local_dir,name),encoding='utf-8').read()
    # Check key indicators
    if name=='preview_server.py':
        ok='render_server_grid' not in local[:300]
        print('{}: import OK={}  chars={}'.format(name,ok,len(local)))
    else:
        n_svr=local.count('def render_server_grid')
        n_exp=local.count('def render_expandable_detail')
        ok=(n_svr==0 and n_exp==0)
        print('{}: dead_funcs_cleaned={}  chars={}'.format(name,ok,len(local)))
c.close()
print('\nDone! Server -> local sync complete.')
